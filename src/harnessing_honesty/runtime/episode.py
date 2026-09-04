"""Episode runners.

One-call smoke, linear pressured, forked branches, shared draft, the 3x3
matrix, and the descriptive multi-turn spine. The matrix is the primary
condition; the spine is kept separate and never produces a matrix cell.
"""


from harnessing_honesty.domain.episodes import (
    StageSnapshot,
    EpisodeRecord,
    BranchRecord,
    ForkedEpisodeRecord,
    DraftForkedRecord,
    MatrixBranchRecord,
    MatrixDraftRecord,
    MatrixEpisodeRecord,
    MultiTurnTurnRecord,
    MultiTurnRecord,
)
from harnessing_honesty.runtime.branching import (
    BranchSpec,
    clone_branch,
    permute_branch_ids,
    unique_branch_ids,
)
from harnessing_honesty.domain import (
    AnswerSuccess,
    Message,
    ModelClient,
    ModelResult,
    PromptView,
    Stage,
)
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily
from harnessing_honesty.domain.matrix import development_conditions
from harnessing_honesty.runtime.policies import DEVELOPMENT_VERIFIER_OUTPUT, policy_follow_ups
from harnessing_honesty.runtime.pressures import (
    PressureTemplate,
    development_pressure_templates,
    wrap_false_counter_position,
)
from harnessing_honesty.runtime.prompt_view import messages_for
from harnessing_honesty.runtime.stages import advance
from harnessing_honesty.runtime.transcript import Transcript


def _bound(client: ModelClient, session: object | None) -> ModelClient:
    wrap = getattr(session, "wrap", None)
    if wrap is None:
        return client
    return wrap(client)


def run_episode(
    prompt: PromptView,
    client: ModelClient,
    session: object | None = None,
) -> ModelResult:
    """Send only the projected question. Used by the live one-call smoke."""
    return _bound(client, session).complete(messages_for(prompt))


def run_pressured_episode(
    prompt: PromptView,
    pressure: str,
    client: ModelClient,
    session: object | None = None,
) -> EpisodeRecord:
    """Run neutral then pressured-final calls.

    The controller owns stage order. Assistant content is the public
    ``AnswerResponse`` JSON only. If the first call is not
    ``AnswerSuccess``, the episode stops and no assistant turn is invented.
    Rendering receives ``prompt`` only; the answer key never enters this
    function.
    """
    client = _bound(client, session)
    transcript = Transcript()
    snapshots: list[StageSnapshot] = []
    current: Stage | None = None

    current = advance(current, Stage.NEUTRAL)
    for message in messages_for(prompt):
        transcript = transcript.append(message)
    request = transcript.snapshot()
    result = client.complete(request)
    snapshots.append(
        StageSnapshot(stage=current, request=request, result=result)
    )

    if not isinstance(result, AnswerSuccess):
        return EpisodeRecord(snapshots=tuple(snapshots))

    current = advance(current, Stage.PRESSURED_FINAL)
    transcript = transcript.append(
        Message(role="assistant", content=result.response.model_dump_json())
    )
    transcript = transcript.append(Message(role="user", content=pressure))
    request = transcript.snapshot()
    result = client.complete(request)
    snapshots.append(
        StageSnapshot(stage=current, request=request, result=result)
    )

    return EpisodeRecord(snapshots=tuple(snapshots))


def run_forked_episode(
    prompt: PromptView,
    branches: tuple[BranchSpec, ...],
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> ForkedEpisodeRecord:
    """Run one neutral call, then isolated pressured-final calls per branch.

    Branch records are returned in spec order. ``order_seed`` only permutes
    ``execution_order``. A failed branch does not skip remaining branches
    and does not append failure text onto another transcript.
    Rendering receives ``prompt`` only; the answer key never enters this
    function.
    """
    spec_ids = unique_branch_ids(branches)
    specs_by_id = {spec.branch_id: spec for spec in branches}
    client = _bound(client, session)

    current = advance(None, Stage.NEUTRAL)
    transcript = Transcript()
    for message in messages_for(prompt):
        transcript = transcript.append(message)
    request = transcript.snapshot()
    result = client.complete(request)
    shared = StageSnapshot(stage=current, request=request, result=result)

    if not isinstance(result, AnswerSuccess):
        return ForkedEpisodeRecord(
            shared=shared,
            branches=(),
            execution_order=(),
        )

    prefix = transcript.append(
        Message(role="assistant", content=result.response.model_dump_json())
    )
    states = {
        branch_id: clone_branch(prefix, current, branch_id)
        for branch_id in spec_ids
    }
    execution_order = permute_branch_ids(spec_ids, order_seed)
    records: dict[str, BranchRecord] = {}

    for branch_id in execution_order:
        spec = specs_by_id[branch_id]
        state = states[branch_id]
        branch_stage = advance(state.stage, Stage.PRESSURED_FINAL)
        branch_transcript = state.transcript.append(
            Message(role="user", content=spec.pressure)
        )
        branch_request = branch_transcript.snapshot()
        branch_result = client.complete(branch_request)
        records[branch_id] = BranchRecord(
            branch_id=branch_id,
            snapshot=StageSnapshot(
                stage=branch_stage,
                request=branch_request,
                result=branch_result,
            ),
        )

    return ForkedEpisodeRecord(
        shared=shared,
        branches=tuple(records[branch_id] for branch_id in spec_ids),
        execution_order=execution_order,
    )

def run_shared_draft_episode(
    prompt: PromptView,
    pressure: str,
    follow_ups: tuple[BranchSpec, ...],
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> DraftForkedRecord:
    """Run neutral, one post-pressure draft, then isolated finals.

    The draft ``complete()`` happens once. Follow-up IDs are cloned from
    that draft prefix. ``order_seed`` permutes execution order only.
    Rendering receives ``prompt`` only; the answer key never enters this
    function.
    """
    spec_ids = unique_branch_ids(follow_ups)
    specs_by_id = {spec.branch_id: spec for spec in follow_ups}
    client = _bound(client, session)

    current = advance(None, Stage.NEUTRAL)
    transcript = Transcript()
    for message in messages_for(prompt):
        transcript = transcript.append(message)
    request = transcript.snapshot()
    result = client.complete(request)
    shared = StageSnapshot(stage=current, request=request, result=result)

    if not isinstance(result, AnswerSuccess):
        return DraftForkedRecord(
            shared=shared,
            draft=None,
            branches=(),
            execution_order=(),
        )

    transcript = transcript.append(
        Message(role="assistant", content=result.response.model_dump_json())
    )
    transcript = transcript.append(Message(role="user", content=pressure))
    current = advance(current, Stage.DRAFT)
    draft_request = transcript.snapshot()
    draft_result = client.complete(draft_request)
    draft = StageSnapshot(
        stage=current, request=draft_request, result=draft_result
    )

    if not isinstance(draft_result, AnswerSuccess):
        return DraftForkedRecord(
            shared=shared,
            draft=draft,
            branches=(),
            execution_order=(),
        )

    prefix = transcript.append(
        Message(
            role="assistant",
            content=draft_result.response.model_dump_json(),
        )
    )
    states = {
        branch_id: clone_branch(prefix, current, branch_id)
        for branch_id in spec_ids
    }
    execution_order = permute_branch_ids(spec_ids, order_seed)
    records: dict[str, BranchRecord] = {}

    for branch_id in execution_order:
        spec = specs_by_id[branch_id]
        state = states[branch_id]
        branch_stage = advance(state.stage, Stage.PRESSURED_FINAL)
        branch_transcript = state.transcript
        if spec.tool_result is not None:
            branch_transcript = branch_transcript.append(
                Message(role="tool", content=spec.tool_result)
            )
        branch_transcript = branch_transcript.append(
            Message(role="user", content=spec.pressure)
        )
        branch_request = branch_transcript.snapshot()
        branch_result = client.complete(branch_request)
        records[branch_id] = BranchRecord(
            branch_id=branch_id,
            snapshot=StageSnapshot(
                stage=branch_stage,
                request=branch_request,
                result=branch_result,
            ),
        )

    return DraftForkedRecord(
        shared=shared,
        draft=draft,
        branches=tuple(records[branch_id] for branch_id in spec_ids),
        execution_order=execution_order,
    )


def _run_matrix(
    prompt: PromptView,
    pressures: tuple[PressureTemplate, ...],
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
    *,
    verifier_output: str,
) -> MatrixEpisodeRecord:
    """Run the 3×3 from one neutral response and the supplied pressure texts."""
    client = _bound(client, session)
    policies = policy_follow_ups(verifier_output)
    pressure_ids = tuple(item.family.value for item in pressures)
    pressures_by_id = {item.family.value: item for item in pressures}
    policy_ids = tuple(spec.branch_id for spec in policies)
    policies_by_id = {spec.branch_id: spec for spec in policies}

    current = advance(None, Stage.NEUTRAL)
    transcript = Transcript()
    for message in messages_for(prompt):
        transcript = transcript.append(message)
    request = transcript.snapshot()
    result = client.complete(request)
    shared = StageSnapshot(stage=current, request=request, result=result)

    if not isinstance(result, AnswerSuccess):
        return MatrixEpisodeRecord(
            shared=shared,
            drafts=(),
            branches=(),
            execution_order=(),
        )

    neutral_prefix = transcript.append(
        Message(role="assistant", content=result.response.model_dump_json())
    )
    pressure_order = permute_branch_ids(pressure_ids, order_seed)
    policy_order = permute_branch_ids(policy_ids, order_seed)

    draft_by_pressure: dict[str, MatrixDraftRecord] = {}
    records: dict[str, MatrixBranchRecord] = {}
    execution_order: list[str] = []

    for pressure_id in pressure_order:
        pressure = pressures_by_id[pressure_id]
        pressure_state = clone_branch(neutral_prefix, Stage.NEUTRAL, pressure_id)
        draft_transcript = pressure_state.transcript.append(
            Message(role="user", content=pressure.text)
        )
        draft_stage = advance(pressure_state.stage, Stage.DRAFT)
        draft_request = draft_transcript.snapshot()
        draft_result = client.complete(draft_request)
        draft = StageSnapshot(
            stage=draft_stage, request=draft_request, result=draft_result
        )
        draft_by_pressure[pressure_id] = MatrixDraftRecord(
            pressure_family=pressure_id, snapshot=draft
        )

        if not isinstance(draft_result, AnswerSuccess):
            continue

        draft_prefix = draft_transcript.append(
            Message(
                role="assistant",
                content=draft_result.response.model_dump_json(),
            )
        )
        for policy_id in policy_order:
            spec = policies_by_id[policy_id]
            condition = Condition(
                pressure=pressure.family,
                policy=PolicyFamily(policy_id),
            )
            state = clone_branch(draft_prefix, draft_stage, condition.identity)
            branch_stage = advance(state.stage, Stage.PRESSURED_FINAL)
            branch_transcript = state.transcript
            if spec.tool_result is not None:
                branch_transcript = branch_transcript.append(
                    Message(role="tool", content=spec.tool_result)
                )
            branch_transcript = branch_transcript.append(
                Message(role="user", content=spec.pressure)
            )
            branch_request = branch_transcript.snapshot()
            branch_result = client.complete(branch_request)
            records[condition.identity] = MatrixBranchRecord(
                condition=condition,
                snapshot=StageSnapshot(
                    stage=branch_stage,
                    request=branch_request,
                    result=branch_result,
                ),
            )
            execution_order.append(condition.identity)

    spec_ids = tuple(item.identity for item in development_conditions())
    return MatrixEpisodeRecord(
        shared=shared,
        drafts=tuple(
            draft_by_pressure[pressure_id]
            for pressure_id in pressure_ids
            if pressure_id in draft_by_pressure
        ),
        branches=tuple(
            records[identity] for identity in spec_ids if identity in records
        ),
        execution_order=tuple(execution_order),
    )


def run_development_matrix(
    prompt: PromptView,
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> MatrixEpisodeRecord:
    """Development 3×3. Orion pressure texts stay on this path only."""
    return _run_matrix(
        prompt,
        development_pressure_templates(),
        client,
        order_seed,
        session,
        verifier_output=DEVELOPMENT_VERIFIER_OUTPUT,
    )


def run_confirmatory_matrix(
    prompt: PromptView,
    counter_position: str,
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
    *,
    verifier_output: str,
) -> MatrixEpisodeRecord:
    """Confirmatory 3×3. Pressure texts wrap the item's false counter-position."""
    return _run_matrix(
        prompt,
        wrap_false_counter_position(counter_position),
        client,
        order_seed,
        session,
        verifier_output=verifier_output,
    )


def _run_multi_turn(
    prompt: PromptView,
    pressures: tuple[PressureTemplate, ...],
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> MultiTurnRecord:
    """Apply every supplied pressure family in a seeded order on one transcript."""
    client = _bound(client, session)
    pressures_by_id = {item.family.value: item for item in pressures}
    pressure_ids = tuple(item.family.value for item in pressures)

    current: Stage | None = advance(None, Stage.NEUTRAL)
    transcript = Transcript()
    for message in messages_for(prompt):
        transcript = transcript.append(message)
    request = transcript.snapshot()
    result = client.complete(request)
    shared = StageSnapshot(stage=current, request=request, result=result)

    if not isinstance(result, AnswerSuccess):
        return MultiTurnRecord(shared=shared, turns=(), pressure_order=())

    transcript = transcript.append(
        Message(role="assistant", content=result.response.model_dump_json())
    )
    pressure_order = permute_branch_ids(pressure_ids, order_seed)
    turns: list[MultiTurnTurnRecord] = []

    for position, pressure_id in enumerate(pressure_order):
        pressure = pressures_by_id[pressure_id]
        current = advance(current, Stage.MULTI_TURN)
        transcript = transcript.append(
            Message(role="user", content=pressure.text)
        )
        turn_request = transcript.snapshot()
        turn_result = client.complete(turn_request)
        turns.append(
            MultiTurnTurnRecord(
                position=position,
                pressure_family=pressure_id,
                snapshot=StageSnapshot(
                    stage=current,
                    request=turn_request,
                    result=turn_result,
                ),
            )
        )

        if not isinstance(turn_result, AnswerSuccess):
            break

        transcript = transcript.append(
            Message(
                role="assistant",
                content=turn_result.response.model_dump_json(),
            )
        )

    return MultiTurnRecord(
        shared=shared,
        turns=tuple(turns),
        pressure_order=pressure_order,
    )


def run_multi_turn_episode(
    prompt: PromptView,
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> MultiTurnRecord:
    """Development spine. Orion pressure texts stay on this path only.

    Descriptive only. Turns accumulate, so turn ``n`` sees turns ``1..n-1``.
    That is the opposite of the matrix, where each cell is isolated. Every
    snapshot is ``Stage.MULTI_TURN``, which cannot reach
    ``Stage.PRESSURED_FINAL``, so these turns cannot be read as matrix
    cells. No policy text and no verifier output are attached here.

    A turn that is not ``AnswerSuccess`` ends the spine; no assistant turn
    is invented from a failure.
    """
    return _run_multi_turn(
        prompt,
        development_pressure_templates(),
        client,
        order_seed,
        session,
    )


def run_confirmatory_multi_turn(
    prompt: PromptView,
    counter_position: str,
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> MultiTurnRecord:
    """Descriptive spine using the item's false counter-position wrappers."""
    return _run_multi_turn(
        prompt,
        wrap_false_counter_position(counter_position),
        client,
        order_seed,
        session,
    )
"""Episode runners.

The one-call serving smoke, the 3x3 matrix, and the descriptive policy loops.
The matrix is the primary condition; loop turns never produce a matrix cell.
"""


from harnessing_honesty.domain.episodes import (
    StageSnapshot,
    MatrixBranchRecord,
    MatrixDraftRecord,
    MatrixEpisodeRecord,
    LoopEpisodeRecord,
    LoopTurnRecord,
    PolicyLoopRecord,
)
from harnessing_honesty.runtime.branching import (
    clone_branch,
    matrix_order,
    permute_branch_ids,
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


def _label(
    client: ModelClient, stage: Stage, cell_identity: str | None, scenario_id: str
) -> None:
    """Record the stage, cell and item of the next call; harness-only, never sent."""
    label = getattr(client, "label", None)
    if label is not None:
        label(stage.value, cell_identity, scenario_id)


def run_episode(
    prompt: PromptView,
    client: ModelClient,
    session: object | None = None,
) -> ModelResult:
    """Send only the projected question. Used by the live one-call smoke."""
    return _bound(client, session).complete(messages_for(prompt))


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
    _label(client, current, None, prompt.id)
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
        Message(role="assistant", content=result.response.answer)
    )
    order = matrix_order(pressure_ids, policy_ids, order_seed)

    draft_by_pressure: dict[str, MatrixDraftRecord] = {}
    records: dict[str, MatrixBranchRecord] = {}
    execution_order: list[str] = []

    for pressure_id, policy_order in order:
        pressure = pressures_by_id[pressure_id]
        pressure_state = clone_branch(neutral_prefix, Stage.NEUTRAL, pressure_id)
        draft_transcript = pressure_state.transcript.append(
            Message(role="user", content=pressure.text)
        )
        draft_stage = advance(pressure_state.stage, Stage.DRAFT)
        draft_request = draft_transcript.snapshot()
        _label(client, draft_stage, pressure_id, prompt.id)
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
                content=draft_result.response.answer,
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
            if spec.external_report is not None:
                branch_transcript = branch_transcript.append(
                    Message(role="user", content=spec.external_report)
                )
            branch_transcript = branch_transcript.append(
                Message(role="user", content=spec.pressure)
            )
            branch_request = branch_transcript.snapshot()
            _label(client, branch_stage, condition.identity, prompt.id)
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


def _run_loops(
    prompt: PromptView,
    pressures: tuple[PressureTemplate, ...],
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
    *,
    verifier_output: str,
) -> LoopEpisodeRecord:
    """One neutral answer, then one loop per policy over the supplied pressures.

    Each loop is an agent loop with a fixed iteration budget [108]: every turn adds
    the next pressure, the policy's text (and, for the tool policy, the
    labelled report), and the model's answer to that loop's own transcript.
    Pressures run in the supplied order in every loop; ``order_seed`` only
    permutes which loop runs first. Loops never stop on an answer's
    correctness, so the calls made do not depend on outcomes.
    """
    client = _bound(client, session)
    policies = {
        PolicyFamily(spec.branch_id): spec
        for spec in policy_follow_ups(verifier_output)
    }

    current = advance(None, Stage.NEUTRAL)
    transcript = Transcript()
    for message in messages_for(prompt):
        transcript = transcript.append(message)
    request = transcript.snapshot()
    _label(client, current, None, prompt.id)
    result = client.complete(request)
    shared = StageSnapshot(stage=current, request=request, result=result)
    if not isinstance(result, AnswerSuccess):
        return LoopEpisodeRecord(shared=shared, loops=(), execution_order=())

    answer = Message(role="assistant", content=result.response.answer)
    prefix = transcript.append(answer)
    order = tuple(
        PolicyFamily(policy)
        for policy in permute_branch_ids(tuple(p.value for p in policies), order_seed)
    )
    loops: dict[PolicyFamily, PolicyLoopRecord] = {}
    for policy in order:
        spec = policies[policy]
        state = clone_branch(prefix, Stage.NEUTRAL, f"loop__{policy.value}")
        stage, loop_transcript = state.stage, state.transcript
        turns: list[LoopTurnRecord] = []
        for position, pressure in enumerate(pressures, start=1):
            stage = advance(stage, Stage.MULTI_TURN)
            loop_transcript = loop_transcript.append(
                Message(role="user", content=pressure.text)
            )
            if spec.external_report is not None:
                loop_transcript = loop_transcript.append(
                    Message(role="user", content=spec.external_report)
                )
            loop_transcript = loop_transcript.append(
                Message(role="user", content=spec.pressure)
            )
            turn_request = loop_transcript.snapshot()
            cell = f"loop__{policy.value}__{pressure.family.value}"
            _label(client, stage, cell, prompt.id)
            turn_result = client.complete(turn_request)
            turns.append(
                LoopTurnRecord(
                    position=position,
                    pressure_family=pressure.family,
                    snapshot=StageSnapshot(
                        stage=stage, request=turn_request, result=turn_result
                    ),
                )
            )
            if not isinstance(turn_result, AnswerSuccess):
                break
            loop_transcript = loop_transcript.append(
                Message(role="assistant", content=turn_result.response.answer)
            )
        loops[policy] = PolicyLoopRecord(policy=policy, turns=tuple(turns))
    return LoopEpisodeRecord(
        shared=shared,
        loops=tuple(loops[policy] for policy in policies),
        execution_order=order,
    )


def run_development_loops(
    prompt: PromptView,
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> LoopEpisodeRecord:
    """Development loops. Orion pressure texts stay on this path only."""
    return _run_loops(
        prompt,
        development_pressure_templates(),
        client,
        order_seed,
        session,
        verifier_output=DEVELOPMENT_VERIFIER_OUTPUT,
    )


def run_confirmatory_loops(
    prompt: PromptView,
    counter_position: str,
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
    *,
    verifier_output: str,
) -> LoopEpisodeRecord:
    """Confirmatory loops: the item's three wrappers in escalating order.

    Contradiction, then authority, then citation: each turn adds rhetorical
    weight to the same false proposition, as escalating rebuttal chains do
    [2], [10]. The descriptive multi-turn substudy follows SYCON-Bench [10].
    """
    return _run_loops(
        prompt,
        wrap_false_counter_position(counter_position),
        client,
        order_seed,
        session,
        verifier_output=verifier_output,
    )

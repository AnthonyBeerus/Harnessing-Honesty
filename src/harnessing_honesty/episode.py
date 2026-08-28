"""Episode runners.

One-call smoke, linear pressured, forked branches, shared draft, the 3x3
matrix, and the descriptive multi-turn spine. The matrix is the primary
condition; the spine is kept separate and never produces a matrix cell.
"""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.branching import (
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
from harnessing_honesty.matrix import development_conditions
from harnessing_honesty.policies import policy_follow_ups
from harnessing_honesty.pressures import development_pressure_templates
from harnessing_honesty.prompt_view import messages_for
from harnessing_honesty.stages import advance
from harnessing_honesty.transcript import Transcript


class StageSnapshot(BaseModel):
    """Immutable record of one ``complete`` call: stage, request, result."""

    model_config = ConfigDict(frozen=True)

    stage: Stage
    request: tuple[Message, ...]
    result: ModelResult


class EpisodeRecord(BaseModel):
    """Ordered snapshots for one episode. A failed first call has length 1."""

    model_config = ConfigDict(frozen=True)

    snapshots: tuple[StageSnapshot, ...]


class BranchRecord(BaseModel):
    """One branch's pressured-final snapshot, keyed by stable identity."""

    model_config = ConfigDict(frozen=True)

    branch_id: str
    snapshot: StageSnapshot


class ForkedEpisodeRecord(BaseModel):
    """One shared neutral snapshot plus isolated branch finals.

    ``branches`` is spec order, not execution order. ``execution_order`` is
    the seeded permutation of IDs. Changing the seed must change only that
    metadata (and the order of later ``complete`` calls), not branch identity.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    branches: tuple[BranchRecord, ...]
    execution_order: tuple[str, ...]

class DraftForkedRecord(BaseModel):
    """One shared neutral, one shared draft, then isolated finals.

    ``branches`` is spec order, not execution order. ``draft`` is None
    when the neutral call is not ``AnswerSuccess``.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    draft: StageSnapshot | None
    branches: tuple[BranchRecord, ...]
    execution_order: tuple[str, ...]


class MatrixBranchRecord(BaseModel):
    """One policy-by-pressure final, keyed by a Condition.

    Pressure, policy, and track live on ``condition``. Identity is derived
    from those members, so a stored label cannot disagree with the cell.
    """

    model_config = ConfigDict(frozen=True)

    condition: Condition
    snapshot: StageSnapshot


class MatrixDraftRecord(BaseModel):
    """One pressure's draft, keyed by family rather than by position.

    The draft is shared by that pressure's three policy cells, so its
    correctness decides whether those cells measure recovery from a
    concession or maintenance of a correct answer. That makes it a mediator
    the scorer has to read, and reading it by list position would let a
    reordering silently attribute a draft to the wrong family.
    """

    model_config = ConfigDict(frozen=True)

    pressure_family: str
    snapshot: StageSnapshot


class MatrixEpisodeRecord(BaseModel):
    """One shared neutral, one draft per pressure, nine isolated finals.

    ``drafts`` and ``branches`` are spec order, not execution order.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    drafts: tuple[MatrixDraftRecord, ...]
    branches: tuple[MatrixBranchRecord, ...]
    execution_order: tuple[str, ...]


class MultiTurnTurnRecord(BaseModel):
    """One pressure turn on the descriptive spine, in delivered order."""

    model_config = ConfigDict(frozen=True)

    position: int
    pressure_family: str
    snapshot: StageSnapshot


class MultiTurnRecord(BaseModel):
    """One neutral answer, then pressures applied in a seeded order.

    This is a descriptive path. Turns accumulate on one transcript, are
    labelled ``Stage.MULTI_TURN``, and never become matrix cells.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    turns: tuple[MultiTurnTurnRecord, ...]
    pressure_order: tuple[str, ...]


def run_episode(
    prompt: PromptView,
    client: ModelClient,
) -> ModelResult:
    """Send only the projected question. Used by the live one-call smoke."""
    return client.complete(messages_for(prompt))


def run_pressured_episode(
    prompt: PromptView,
    pressure: str,
    client: ModelClient,
) -> EpisodeRecord:
    """Run neutral then pressured-final calls.

    The controller owns stage order. Assistant content is the public
    ``AnswerResponse`` JSON only. If the first call is not
    ``AnswerSuccess``, the episode stops and no assistant turn is invented.
    Rendering receives ``prompt`` only; the answer key never enters this
    function.
    """
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
) -> DraftForkedRecord:
    """Run neutral, one post-pressure draft, then isolated finals.

    The draft ``complete()`` happens once. Follow-up IDs are cloned from
    that draft prefix. ``order_seed`` permutes execution order only.
    Rendering receives ``prompt`` only; the answer key never enters this
    function.
    """
    spec_ids = unique_branch_ids(follow_ups)
    specs_by_id = {spec.branch_id: spec for spec in follow_ups}

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


def run_development_matrix(
    prompt: PromptView,
    client: ModelClient,
    order_seed: int,
) -> MatrixEpisodeRecord:
    """Run the 3×3 matrix from one neutral response.

    Each pressure family gets one draft. Each draft is cloned into three
    policy finals. ``order_seed`` permutes pressure order and, with the
    same seed, policy order inside each pressure.
    """
    pressures = development_pressure_templates()
    policies = policy_follow_ups()
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


def run_multi_turn_episode(
    prompt: PromptView,
    client: ModelClient,
    order_seed: int,
) -> MultiTurnRecord:
    """Apply every pressure family in a seeded order on one transcript.

    Descriptive only. Turns accumulate, so turn ``n`` sees turns ``1..n-1``.
    That is the opposite of the matrix, where each cell is isolated. Every
    snapshot is ``Stage.MULTI_TURN``, which cannot reach
    ``Stage.PRESSURED_FINAL``, so these turns cannot be read as matrix
    cells. No policy text and no verifier output are attached here.

    A turn that is not ``AnswerSuccess`` ends the spine; no assistant turn
    is invented from a failure.
    """
    pressures = development_pressure_templates()
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
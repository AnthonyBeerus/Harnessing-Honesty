"""Episode runners: one-call smoke, linear pressured, and forked branches."""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.branching import (
    BranchSpec,
    clone_branch,
    permute_branch_ids,
    unique_branch_ids,
)
from harnessing_honesty.models import (
    AnswerSuccess,
    Message,
    ModelClient,
    ModelResult,
)
from harnessing_honesty.prompt_view import PromptView, messages_for
from harnessing_honesty.stages import Stage, advance
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
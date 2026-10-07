"""Rebuild matrix and loop episodes, and matrix rows, from a run directory.

Inputs are the saved requests, the raw outcome events and the runner's call
labels. Scores are computed again by ``score_matrix_episode`` and
``score_loop_episode``; no stored score supplies a value.
"""

from collections.abc import Mapping
from pathlib import Path

from harnessing_honesty.analysis.rows import AnalysisRow, exclusion_reason
from harnessing_honesty.domain import Message
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily, Stage
from harnessing_honesty.domain.episodes import (
    LoopEpisodeRecord,
    LoopTurnRecord,
    MatrixBranchRecord,
    MatrixDraftRecord,
    MatrixEpisodeRecord,
    PolicyLoopRecord,
    StageSnapshot,
)
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.domain.matrix import development_conditions
from harnessing_honesty.domain.results import ModelResult
from harnessing_honesty.observability.integrity import require_integrity
from harnessing_honesty.observability.reconstruct import (
    ReconstructedRun,
    reconstruct_run,
    recorded_result,
    saved_request,
)
from harnessing_honesty.scoring import (
    LOOP_PRESSURES,
    MatrixEpisodeScore,
    score_matrix_episode,
)

_Call = tuple[RequestSent, Stage, tuple[Message, ...], ModelResult | None]


def rows_from_matrix_score(
    run_id: str,
    scenario_id: str,
    scored: MatrixEpisodeScore,
    *,
    task_stratum: str | None = None,
) -> tuple[AnalysisRow, ...]:
    """Project a scored matrix onto analysis rows."""
    return tuple(
        AnalysisRow(
            run_id=run_id,
            scenario_id=scenario_id,
            condition=cell.condition,
            initial_state=cell.score.initial_state,
            draft_state=cell.draft_state,
            final_state=cell.score.final_state,
            eligible=cell.score.eligible,
            eligibility=cell.eligibility,
            initial_correct=cell.score.initial_correct,
            final_correct=cell.score.final_correct,
            regressive_shift=cell.score.regressive_shift,
            draft_correct=cell.draft_correct,
            final_answer=cell.score.final_answer,
            final_raw_response=cell.score.final_raw_response,
            valid=cell.score.valid,
            exclusion=exclusion_reason(cell.eligibility, cell.score.final_state),
            task_stratum=task_stratum,
        )
        for cell in scored.cells
    )


def require_closed_matrix(
    run_dir: Path, block_id: str | None = None
) -> MatrixEpisodeRecord:
    """Rebuild the matrix of a run that closed; an open run is refused."""
    require_integrity(run_dir)
    if reconstruct_run(run_dir).interrupted:
        raise ValueError("run is incomplete")
    return _matrix_record(run_dir, block_id)


def matrix_record_from_run(
    run_dir: Path, block_id: str | None = None
) -> MatrixEpisodeRecord:
    """Rebuild one matrix episode from its saved requests and raw outcomes.

    Each logical call is read from its last attempt. A call whose last
    attempt is indeterminate fills no slot, so scoring reads it as missing;
    an indeterminate neutral leaves no matrix to score. A run directory that
    fails its integrity checks raises ``IntegrityError``.
    """
    require_integrity(run_dir)
    return _matrix_record(run_dir, block_id)


def rows_from_run(
    run_dir: Path, items: Mapping[str, InstrumentItem]
) -> tuple[AnalysisRow, ...]:
    """Every matrix block of a closed collection run, scored and projected to rows.

    Integrity is checked once for the run. Each block is rebuilt from its
    saved requests and raw outcomes, attributed to the item its calls name,
    scored against that item's key and given the item's stratum. Loop blocks
    give no matrix rows; ``analysis.loops`` reads them.
    """
    rebuilt = closed_run(run_dir)
    rows: list[AnalysisRow] = []
    for block_id, (item_id, loop) in run_blocks(rebuilt).items():
        if loop:
            continue
        item = items[item_id]
        scored = score_matrix_episode(
            _matrix_record(run_dir, block_id, rebuilt), item.answer_key
        )
        rows.extend(
            rows_from_matrix_score(
                rebuilt.record.run_id,
                item_id,
                scored,
                task_stratum=item.stratum.value,
            )
        )
    return tuple(rows)


def closed_run(run_dir: Path) -> ReconstructedRun:
    """A run that passes its integrity checks and closed; others are refused."""
    require_integrity(run_dir)
    rebuilt = reconstruct_run(run_dir)
    if rebuilt.interrupted:
        raise ValueError("run is incomplete")
    return rebuilt


def run_blocks(rebuilt: ReconstructedRun) -> dict[str, tuple[str, bool]]:
    """Each block's item and whether it is a loop block, in recorded order.

    A block whose calls name no item, or that mixes loop turns with matrix
    calls, is refused.
    """
    items: dict[str, str | None] = {}
    kinds: dict[str, set[bool]] = {}
    for event in rebuilt.events:
        if not isinstance(event, RequestSent):
            continue
        block_id = str(event.block_id)
        items.setdefault(block_id, event.scenario_id)
        stages = kinds.setdefault(block_id, set())
        if event.stage != Stage.NEUTRAL:
            stages.add(event.stage == Stage.MULTI_TURN)
    found: dict[str, tuple[str, bool]] = {}
    for block_id, item_id in items.items():
        if item_id is None:
            raise ValueError(f"{block_id} names no item")
        if len(kinds[block_id]) > 1:
            raise ValueError(f"{block_id} mixes loop turns and matrix calls")
        found[block_id] = (item_id, kinds[block_id] == {True})
    return found


def loop_record_from_run(
    run_dir: Path, block_id: str, rebuilt: ReconstructedRun | None = None
) -> LoopEpisodeRecord:
    """Rebuild one loop block from its saved requests and raw outcomes.

    Each call is read from its last attempt. The runner sends a loop's turns
    in order, so only its last recorded turn can lack a determinate result;
    that turn is dropped and scoring reads it as missing. Turns that do not
    run 1, 2, ... in call order are refused.
    """
    calls = _block_calls(run_dir, block_id, rebuilt or reconstruct_run(run_dir))
    shared = _shared(block_id, calls)
    positions = {family.value: n for n, family in enumerate(LOOP_PRESSURES, start=1)}
    found: dict[PolicyFamily, list[LoopTurnRecord]] = {}
    for request, stage, messages, result in calls:
        if stage is Stage.NEUTRAL:
            continue
        if stage is not Stage.MULTI_TURN:
            raise ValueError(f"stage {stage} is not part of a loop")
        prefix, policy, pressure = str(request.cell_identity).split("__")
        if prefix != "loop":
            raise ValueError(f"cell {request.cell_identity} is not a loop turn")
        turns = found.setdefault(PolicyFamily(policy), [])
        if result is None:
            continue
        if positions[pressure] != len(turns) + 1:
            cell = request.cell_identity
            raise ValueError(f"{block_id}: loop turn {cell} out of order")
        turns.append(
            LoopTurnRecord(
                position=positions[pressure],
                pressure_family=PressureFamily(pressure),
                snapshot=StageSnapshot(stage=stage, request=messages, result=result),
            )
        )
    return LoopEpisodeRecord(
        shared=shared,
        loops=tuple(
            PolicyLoopRecord(policy=policy, turns=tuple(found[policy]))
            for policy in PolicyFamily
            if policy in found
        ),
        execution_order=tuple(found),
    )


def _block_calls(
    run_dir: Path, block_id: str, rebuilt: ReconstructedRun
) -> list[_Call]:
    """The last attempt of every call in ``block_id``, in call order."""
    events = rebuilt.events
    last: dict[str, int] = {}
    for attempt in rebuilt.attempts:
        request = events[attempt.request_sequence]
        if not isinstance(request, RequestSent) or request.block_id != block_id:
            continue
        if attempt.call_id is None:
            raise ValueError("run predates call identities")
        last[attempt.call_id] = attempt.request_sequence
    calls: list[_Call] = []
    for sequence in last.values():
        request = events[sequence]
        assert isinstance(request, RequestSent)
        if request.stage is None:
            raise ValueError(f"call {request.call_id} has no stage label")
        messages = _saved_request(run_dir, request)
        outcome = events[sequence + 1] if sequence + 1 < len(events) else None
        result = recorded_result(outcome, messages)
        calls.append((request, Stage(request.stage), messages, result))
    return calls


def _shared(block_id: str, calls: list[_Call]) -> StageSnapshot:
    """The block's one neutral call, which must have a determinate result."""
    neutral = [call for call in calls if call[1] is Stage.NEUTRAL]
    if not neutral:
        raise ValueError(f"block {block_id} has no neutral call")
    if len(neutral) > 1:
        raise ValueError("block has more than one neutral call")
    _, stage, messages, result = neutral[0]
    if result is None:
        raise ValueError("neutral call has no determinate result")
    return StageSnapshot(stage=stage, request=messages, result=result)


def _matrix_record(
    run_dir: Path, block_id: str | None, rebuilt: ReconstructedRun | None = None
) -> MatrixEpisodeRecord:
    rebuilt = rebuilt or reconstruct_run(run_dir)
    if block_id is None:
        sent = [event for event in rebuilt.events if isinstance(event, RequestSent)]
        blocks = sorted({str(event.block_id) for event in sent})
        if len(blocks) != 1:
            raise ValueError(f"run has blocks {blocks}; choose one")
        block_id = blocks[0]
    calls = _block_calls(run_dir, block_id, rebuilt)
    shared = _shared(block_id, calls)
    drafts: dict[str, MatrixDraftRecord] = {}
    branches: dict[str, MatrixBranchRecord] = {}
    execution_order: list[str] = []
    for request, stage, messages, result in calls:
        if stage is Stage.NEUTRAL or result is None:
            continue
        snapshot = StageSnapshot(stage=stage, request=messages, result=result)
        cell = str(request.cell_identity)
        if stage is Stage.DRAFT:
            drafts[cell] = MatrixDraftRecord(pressure_family=cell, snapshot=snapshot)
        elif stage is Stage.PRESSURED_FINAL:
            pressure, _, policy = cell.partition("__")
            condition = Condition(
                pressure=PressureFamily(pressure),
                policy=PolicyFamily(policy),
                track=rebuilt.record.track,
            )
            branches[cell] = MatrixBranchRecord(condition=condition, snapshot=snapshot)
            execution_order.append(cell)
        else:
            raise ValueError(f"stage {stage} is not part of the matrix")
    expected = development_conditions()
    families = tuple(dict.fromkeys(item.pressure.value for item in expected))
    return MatrixEpisodeRecord(
        shared=shared,
        drafts=tuple(drafts[family] for family in families if family in drafts),
        branches=tuple(
            branches[item.identity] for item in expected if item.identity in branches
        ),
        execution_order=tuple(execution_order),
    )


def _saved_request(run_dir: Path, request: RequestSent) -> tuple[Message, ...]:
    """Load the saved messages; ``require_integrity`` has checked their hash."""
    messages = saved_request(run_dir, str(request.request_hash))
    if len(messages) != request.requested_message_count:
        raise ValueError(f"request {request.request_hash} has the wrong message count")
    return messages

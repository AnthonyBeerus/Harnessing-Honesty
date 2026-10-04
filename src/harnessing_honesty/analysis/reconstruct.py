"""Rebuild a matrix episode and its analysis rows from a run directory.

Inputs are the saved requests, the raw outcome events and the runner's call
labels. Scores are computed again by ``score_matrix_episode``; no stored score
supplies a value.
"""

import json
from pathlib import Path

from harnessing_honesty.analysis.rows import AnalysisRow, exclusion_reason
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
    normalize_binary_answer,
)
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import Failure, PolicyFamily, PressureFamily, Stage
from harnessing_honesty.domain.episodes import (
    MatrixBranchRecord,
    MatrixDraftRecord,
    MatrixEpisodeRecord,
    StageSnapshot,
)
from harnessing_honesty.domain.events import (
    DomainEvent,
    RequestFailed,
    RequestSent,
    ResponseReceived,
)
from harnessing_honesty.domain.matrix import development_conditions
from harnessing_honesty.observability.hashing import digest_text
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.scoring import MatrixEpisodeScore


def rows_from_matrix_score(
    run_id: str,
    scenario_id: str,
    scored: MatrixEpisodeScore,
    *,
    task_stratum: str | None = None,
) -> tuple[AnalysisRow, ...]:
    """Project a scored matrix onto analysis rows.

    Events witness that the run closed and that the call count matches.
    Scores remain the source of the booleans: events do not store answers.
    """
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
    if reconstruct_run(run_dir).interrupted:
        raise ValueError("run is incomplete")
    return matrix_record_from_run(run_dir, block_id)


def matrix_record_from_run(
    run_dir: Path, block_id: str | None = None
) -> MatrixEpisodeRecord:
    """Rebuild one matrix episode from its saved requests and raw outcomes.

    Each logical call is read from its last attempt. A call whose last
    attempt is indeterminate fills no slot, so scoring reads it as missing;
    an indeterminate neutral leaves no matrix to score.
    """
    rebuilt = reconstruct_run(run_dir)
    events = rebuilt.events
    sent = [event for event in events if isinstance(event, RequestSent)]
    if block_id is None:
        blocks = sorted({str(event.block_id) for event in sent})
        if len(blocks) != 1:
            raise ValueError(f"run has blocks {blocks}; choose one")
        block_id = blocks[0]
    last: dict[str, int] = {}
    for attempt in rebuilt.attempts:
        request = events[attempt.request_sequence]
        if not isinstance(request, RequestSent) or request.block_id != block_id:
            continue
        if attempt.call_id is None:
            raise ValueError("run predates call identities")
        last[attempt.call_id] = attempt.request_sequence

    shared: StageSnapshot | None = None
    drafts: dict[str, MatrixDraftRecord] = {}
    branches: dict[str, MatrixBranchRecord] = {}
    execution_order: list[str] = []
    for sequence in last.values():
        request = events[sequence]
        assert isinstance(request, RequestSent)
        if request.stage is None:
            raise ValueError(f"call {request.call_id} has no stage label")
        stage = Stage(request.stage)
        messages = _saved_request(run_dir, request)
        outcome = events[sequence + 1] if sequence + 1 < len(events) else None
        result = _result(outcome, messages)
        if stage is Stage.NEUTRAL:
            if shared is not None:
                raise ValueError("block has more than one neutral call")
            if result is None:
                raise ValueError("neutral call has no determinate result")
            shared = StageSnapshot(stage=stage, request=messages, result=result)
            continue
        if result is None:
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
    if shared is None:
        raise ValueError(f"block {block_id} has no neutral call")
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
    """Load the saved messages and check them against the recorded hash."""
    path = run_dir / "requests" / f"{request.request_hash}.json"
    text = path.read_text(encoding="utf-8")
    if digest_text(text) != request.request_hash:
        raise ValueError(f"saved request {path.name} does not match its hash")
    messages = tuple(Message.model_validate(item) for item in json.loads(text))
    if len(messages) != request.requested_message_count:
        raise ValueError(f"saved request {path.name} has the wrong message count")
    return messages


def _result(
    outcome: DomainEvent | None, messages: tuple[Message, ...]
) -> ModelResult | None:
    """Re-derive a result: parse raw text again; keep transport failures.

    Provider and protocol failures are recorded serving facts, not scores.
    Interrupted or absent outcomes are indeterminate and return ``None``.
    """
    if isinstance(outcome, RequestFailed) and outcome.failure is Failure.PROVIDER:
        return ProviderFailure(detail=outcome.detail)
    if isinstance(outcome, RequestFailed) and outcome.failure is Failure.PROTOCOL:
        return ProtocolFailure(detail=outcome.detail)
    if not isinstance(outcome, ResponseReceived | RequestFailed):
        return None
    raw = outcome.raw_response
    answer = None if raw is None else normalize_binary_answer(raw)
    if raw is None or answer is None:
        return ParseFailure(detail="reconstructed: not yes or no", raw_response=raw)
    return AnswerSuccess(
        response=AnswerResponse(answer=answer),
        raw_response=raw,
        requested_message_count=len(messages),
        observed_message_count=getattr(outcome, "observed_message_count", None),
    )

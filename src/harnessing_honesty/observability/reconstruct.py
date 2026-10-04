"""Rebuild a run from files alone. If this fails, the vocabulary is wrong."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter

from harnessing_honesty.domain.enums import Failure, RecordStatus
from harnessing_honesty.domain.events import (
    AttemptInterrupted,
    DomainEvent,
    RequestFailed,
    RequestSent,
    ResponseReceived,
    UsageCounts,
)
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.records import RunRecord
from harnessing_honesty.domain.responses import normalize_binary_answer

_EVENT_ADAPTER = TypeAdapter(DomainEvent)

AttemptOutcome = Literal["answered", "failed", "interrupted", "no_outcome"]
_EVIDENCE = (
    "raw_response",
    "observed_model",
    "observed_endpoint",
    "observed_snapshot",
    "cache_status",
    "finish_reason",
    "usage",
    "envelope_ref",
    "envelope_hash",
)


class AttemptRecord(BaseModel):
    """One dispatch attempt, what followed it, and its serving evidence.

    ``interrupted`` and ``no_outcome`` are indeterminate: the provider may
    or may not have answered. Serving fields are copied from the outcome
    event and stay ``None`` when it does not state them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_sequence: int
    call_id: str | None
    attempt: int
    request_hash: str | None
    parent_call_id: str | None
    outcome: AttemptOutcome
    failure: Failure | None = None
    block_id: str | None = None
    stage: str | None = None
    cell_identity: str | None = None
    prefix_hash: str | None = None
    raw_response: str | None = None
    observed_model: str | None = None
    observed_endpoint: str | None = None
    observed_snapshot: str | None = None
    cache_status: str | None = None
    finish_reason: str | None = None
    usage: UsageCounts | None = None
    envelope_ref: str | None = None
    envelope_hash: str | None = None

    @property
    def indeterminate(self) -> bool:
        return self.outcome in {"interrupted", "no_outcome"}

    @property
    def parse_agrees(self) -> bool | None:
        """Whether parsing the raw text again agrees with the recorded outcome.

        Only answers and parse failures with raw text are compared; anything
        else, including runs recorded before raw text was kept, gives ``None``.
        """
        if self.raw_response is None:
            return None
        reparsed = normalize_binary_answer(self.raw_response) is not None
        if self.outcome == "answered":
            return reparsed
        if self.failure is Failure.PARSE:
            return not reparsed
        return None


class ReconstructedRun:
    """Events plus the derived summary, loaded from a run directory."""

    def __init__(self, record: RunRecord, events: tuple[DomainEvent, ...]) -> None:
        self.record = record
        self.events = events

    @property
    def attempts(self) -> tuple[AttemptRecord, ...]:
        """Pair each RequestSent with the outcome event that follows it.

        Dispatch is sequential, so an attempt's outcome is the next event.
        An outcome for a different call or attempt is a lineage error.
        """
        records: list[AttemptRecord] = []
        for index, event in enumerate(self.events):
            if not isinstance(event, RequestSent):
                continue
            following = self.events[index + 1] if index + 1 < len(self.events) else None
            outcome: AttemptOutcome = "no_outcome"
            failure: Failure | None = None
            if isinstance(following, ResponseReceived | RequestFailed | AttemptInterrupted):
                if (following.call_id, following.attempt) != (event.call_id, event.attempt):
                    raise ValueError(
                        f"outcome at sequence {following.sequence} does not "
                        f"match request at {event.sequence}"
                    )
                if isinstance(following, ResponseReceived):
                    outcome = "answered"
                elif isinstance(following, RequestFailed):
                    outcome, failure = "failed", following.failure
                else:
                    outcome = "interrupted"
            evidence = {name: getattr(following, name, None) for name in _EVIDENCE}
            records.append(
                AttemptRecord(
                    request_sequence=event.sequence,
                    call_id=event.call_id,
                    attempt=event.attempt,
                    request_hash=event.request_hash,
                    parent_call_id=event.parent_call_id,
                    outcome=outcome,
                    failure=failure,
                    block_id=event.block_id,
                    stage=event.stage,
                    cell_identity=event.cell_identity,
                    prefix_hash=event.prefix_hash,
                    **evidence,
                )
            )
        return tuple(records)

    @property
    def complete_calls(self) -> int:
        return sum(
            1
            for event in self.events
            if event.kind in {"request_sent"}
        )

    @property
    def interrupted(self) -> bool:
        return self.record.status is RecordStatus.INCOMPLETE


_MESSAGES = TypeAdapter(tuple[Message, ...])


def saved_request(run_dir: Path, digest: str) -> tuple[Message, ...]:
    """The messages saved before dispatch under ``requests/{digest}.json``."""
    path = run_dir / "requests" / f"{digest}.json"
    return _MESSAGES.validate_json(path.read_text(encoding="utf-8"))


def reconstruct_run(run_dir: Path) -> ReconstructedRun:
    """Read ``events.jsonl`` and ``summary.json`` with no other inputs."""
    summary_path = run_dir / "summary.json"
    events_path = run_dir / "events.jsonl"
    record = RunRecord.model_validate_json(summary_path.read_text(encoding="utf-8"))
    events: list[DomainEvent] = []
    text = events_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.strip():
            continue
        events.append(_EVENT_ADAPTER.validate_json(line))
    sequences = [event.sequence for event in events]
    if sequences != list(range(len(sequences))):
        raise ValueError(f"event sequence is not dense from 0: {sequences}")
    if events and events[0].run_id != record.run_id:
        raise ValueError("event run_id does not match summary")
    return ReconstructedRun(record, tuple(events))

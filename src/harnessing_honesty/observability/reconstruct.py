"""Rebuild a run from files alone. If this fails, the vocabulary is wrong."""

from pathlib import Path

from pydantic import TypeAdapter

from harnessing_honesty.domain.enums import RecordStatus
from harnessing_honesty.domain.events import DomainEvent
from harnessing_honesty.domain.records import RunRecord

_EVENT_ADAPTER = TypeAdapter(DomainEvent)


class ReconstructedRun:
    """Events plus the derived summary, loaded from a run directory."""

    def __init__(self, record: RunRecord, events: tuple[DomainEvent, ...]) -> None:
        self.record = record
        self.events = events

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

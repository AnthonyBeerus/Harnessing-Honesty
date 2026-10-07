"""Sink-owned monotonic sequence. Events are append-only; summaries replace."""

from pydantic import TypeAdapter

from harnessing_honesty.domain.events import DomainEvent
from harnessing_honesty.domain.protocols import SequencedEvent
from harnessing_honesty.observability.redact import redact_text
from harnessing_honesty.observability.store import FilesystemRecordStore

_EVENT_ADAPTER = TypeAdapter(DomainEvent)


class NullSink:
    """Default sink. Records nothing."""

    def emit(self, event: SequencedEvent) -> None:
        return None


class JsonlEventSink:
    """Assigns and checks sequence. Persists one JSON object per line."""

    def __init__(
        self, store: FilesystemRecordStore, run_id: str, start: int = 0
    ) -> None:
        self._store = store
        self._run_id = run_id
        self._next = start

    @property
    def next_sequence(self) -> int:
        return self._next

    def emit(self, event: SequencedEvent) -> None:
        if event.run_id != self._run_id:
            raise ValueError(
                f"event run_id {event.run_id!r} does not match sink {self._run_id!r}"
            )
        if event.sequence != self._next:
            raise ValueError(
                f"sequence {event.sequence} is not the next expected {self._next}"
            )
        parsed = _EVENT_ADAPTER.validate_python(
            event.model_dump() if hasattr(event, "model_dump") else event
        )
        line = redact_text(parsed.model_dump_json())
        self._store.append(self._run_id, line)
        self._next += 1

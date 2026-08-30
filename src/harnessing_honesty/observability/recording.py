"""Wrap a model client so every complete() is an audit event."""

from datetime import datetime

from harnessing_honesty.domain.enums import RecordStatus, Track
from harnessing_honesty.domain.events import (
    RequestFailed,
    RequestSent,
    ResponseReceived,
    RunClosed,
    RunStarted,
)
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.records import RunRecord
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ModelResult,
    failure_class,
)
from harnessing_honesty.observability.clock import SystemClock
from harnessing_honesty.observability.hashing import request_hash
from harnessing_honesty.observability.sink import JsonlEventSink, NullSink
from harnessing_honesty.observability.store import FilesystemRecordStore


class RunSession:
    """Owns sequence, writes INCOMPLETE first, replaces on close."""

    def __init__(
        self,
        store: FilesystemRecordStore,
        run_id: str,
        requested_model: str,
        seed: int,
        *,
        clock: object | None = None,
        config_hash: str | None = None,
        track: Track = Track.DEV,
        freeze_id: str | None = None,
        scheduler_seed: int | None = None,
        sampling_seed: int | None = None,
        requested_endpoint: str | None = None,
    ) -> None:
        self.run_id = run_id
        self.requested_model = requested_model
        self.requested_endpoint = requested_endpoint
        self._clock = clock or SystemClock()
        self._store = store
        store.create(run_id)
        self.sink = JsonlEventSink(store, run_id)
        self.record = RunRecord(
            run_id=run_id,
            requested_model=requested_model,
            seed=seed,
            status=RecordStatus.INCOMPLETE,
            config_hash=config_hash,
            track=track,
            freeze_id=freeze_id,
            scheduler_seed=scheduler_seed,
            sampling_seed=sampling_seed,
        )
        self._store.replace_summary(run_id, self.record.model_dump_json())

    def _now(self) -> datetime:
        return self._clock.now()

    def start(self) -> None:
        self.sink.emit(
            RunStarted(
                sequence=self.sink.next_sequence,
                run_id=self.run_id,
                occurred_at=self._now(),
                requested_model=self.requested_model,
                config_hash=self.record.config_hash,
                track=self.record.track,
            )
        )

    def close(self, status: RecordStatus = RecordStatus.COMPLETE) -> None:
        self.sink.emit(
            RunClosed(
                sequence=self.sink.next_sequence,
                run_id=self.run_id,
                occurred_at=self._now(),
                status=status,
            )
        )
        self.record = self.record.model_copy(update={"status": status})
        self._store.replace_summary(self.run_id, self.record.model_dump_json())

    def wrap(self, client: object) -> "RecordingModelClient":
        return RecordingModelClient(client, self)


class RecordingModelClient:
    """Emit RequestSent then ResponseReceived or RequestFailed."""

    def __init__(self, inner: object, session: RunSession) -> None:
        self._inner = inner
        self._session = session
        self.stage: str | None = None
        self.cell_identity: str | None = None
        self.verification_report_ids: tuple[str, ...] = ()
        self.attempt: int = 1

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        digest = request_hash(messages)
        self._session.sink.emit(
            RequestSent(
                sequence=self._session.sink.next_sequence,
                run_id=self._session.run_id,
                occurred_at=self._session._now(),
                requested_message_count=len(messages),
                requested_model=self._session.requested_model,
                requested_endpoint=self._session.requested_endpoint,
                request_hash=digest,
                attempt=self.attempt,
                stage=self.stage,
                cell_identity=self.cell_identity,
                verification_report_ids=self.verification_report_ids,
            )
        )
        result: ModelResult = self._inner.complete(messages)  # type: ignore[attr-defined]
        failure = failure_class(result)
        if failure is None:
            assert isinstance(result, AnswerSuccess)
            self._session.sink.emit(
                ResponseReceived(
                    sequence=self._session.sink.next_sequence,
                    run_id=self._session.run_id,
                    occurred_at=self._session._now(),
                    observed_message_count=result.observed_message_count,
                    observed_model=self._session.requested_model,
                    observed_endpoint=self._session.requested_endpoint,
                    attempt=self.attempt,
                    verification_report_ids=self.verification_report_ids,
                )
            )
        else:
            self._session.sink.emit(
                RequestFailed(
                    sequence=self._session.sink.next_sequence,
                    run_id=self._session.run_id,
                    occurred_at=self._session._now(),
                    failure=failure,
                    detail=getattr(result, "detail", failure.value),
                    observed_model=self._session.requested_model,
                    observed_endpoint=self._session.requested_endpoint,
                    attempt=self.attempt,
                )
            )
        return result


def maybe_wrap(
    client: object,
    sink: object | None,
) -> object:
    """Keep existing runners working when no durable sink is supplied."""
    if sink is None or isinstance(sink, NullSink):
        return client
    return sink

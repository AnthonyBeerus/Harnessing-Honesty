"""Wrap a model client so every complete() is an audit event."""

from datetime import datetime
from pathlib import Path
from typing import TypedDict

from harnessing_honesty.domain.enums import RecordStatus, Track
from harnessing_honesty.domain.events import (
    AttemptInterrupted,
    RequestFailed,
    RequestSent,
    ResponseReceived,
    RunClosed,
    RunResumed,
    RunStarted,
    UsageCounts,
)
from harnessing_honesty.domain.evidence import CallEvidence
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.protocols import Clock
from harnessing_honesty.domain.records import RunRecord
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ModelResult,
    failure_class,
)
from harnessing_honesty.observability.clock import SystemClock
from harnessing_honesty.observability.hashing import (
    canonical_request,
    continuation_hash,
    digest_text,
    request_hash,
)
from harnessing_honesty.domain.responses import normalize_binary_answer
from harnessing_honesty.observability.integrity import (
    Integrity,
    IntegrityError,
    check_integrity,
)
from harnessing_honesty.observability.reconstruct import reconstruct_run, saved_request
from harnessing_honesty.observability.redact import redact_text
from harnessing_honesty.observability.sink import JsonlEventSink, NullSink
from harnessing_honesty.observability.store import (
    FilesystemRecordStore,
    set_aside_tail,
)


class _Observed(TypedDict, total=False):
    observed_model: str | None
    observed_endpoint: str | None
    observed_snapshot: str | None
    cache_status: str | None
    generation_id: str | None
    finish_reason: str | None
    usage: UsageCounts | None
    envelope_ref: str
    envelope_hash: str


class RunSession:
    """Owns sequence, writes INCOMPLETE first, replaces on close."""

    def __init__(
        self,
        store: FilesystemRecordStore,
        run_id: str,
        requested_model: str,
        seed: int,
        *,
        clock: Clock | None = None,
        config_hash: str | None = None,
        track: Track = Track.DEV,
        freeze_id: str | None = None,
        scheduler_seed: int | None = None,
        sampling_seed: int | None = None,
        requested_endpoint: str | None = None,
        resume: bool = False,
    ) -> None:
        self.run_id = run_id
        self.requested_model = requested_model
        self.requested_endpoint = requested_endpoint
        self._clock = clock or SystemClock()
        self._store = store
        self._blocks = 0
        self._calls = 0
        self._continuations: dict[str, str] = {}
        self._unfinished_tail: str | None = None
        if resume:
            self._restore(config_hash)
            return
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

    def _restore(self, config_hash: str | None) -> None:
        """Continue an incomplete run: sequence, counters and answered prefixes.

        A closed run, a different configuration or an integrity failure is
        refused. A request saved just before a crash, with no ``RequestSent``,
        is the one exception: resuming re-saves and references it.
        """
        run_dir = self.run_dir
        issues = tuple(
            issue
            for issue in check_integrity(run_dir)
            if not (
                issue.kind is Integrity.UNREFERENCED_FILE
                and issue.where.startswith("requests/")
            )
        )
        if issues:
            raise IntegrityError(issues)
        rebuilt = reconstruct_run(run_dir)
        if not rebuilt.interrupted:
            raise ValueError(f"run {self.run_id} is closed")
        if rebuilt.record.config_hash != config_hash:
            raise ValueError(f"run {self.run_id} was recorded under another config")
        self.record = rebuilt.record
        if rebuilt.unfinished_tail is not None:
            name = f"events-unfinished-{len(rebuilt.events):06d}.txt"
            set_aside_tail(self._store.events_path(self.run_id), name)
            self._unfinished_tail = name
        self.sink = JsonlEventSink(self._store, self.run_id, start=len(rebuilt.events))
        attempts = rebuilt.attempts
        self._blocks = len({attempt.block_id for attempt in attempts})
        self._calls = len({attempt.call_id for attempt in attempts})
        for attempt in attempts:
            answer = normalize_binary_answer(attempt.raw_response or "")
            if attempt.outcome != "answered" or answer is None:
                continue
            messages = saved_request(run_dir, str(attempt.request_hash))
            prefix = continuation_hash(messages, answer)
            self._continuations[prefix] = str(attempt.call_id)

    @property
    def run_dir(self) -> Path:
        return self._store.run_dir(self.run_id)

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

    def resumed(self) -> None:
        self.sink.emit(
            RunResumed(
                sequence=self.sink.next_sequence,
                run_id=self.run_id,
                occurred_at=self._now(),
                unfinished_tail=self._unfinished_tail,
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

    def write_envelope(self, ref: str, payload: str) -> str:
        """Write transport evidence, redacted like events; return its hash."""
        redacted = redact_text(payload)
        self._store.write_envelope(self.run_id, ref, redacted)
        return digest_text(redacted)

    def save_request(self, messages: tuple[Message, ...]) -> str:
        """Save the exact messages before dispatch; return their hash.

        Redaction applies here too. If it changes the text, the saved file no
        longer matches its hash, and reconstruction reports the mismatch.
        """
        digest = request_hash(messages)
        self._store.write_request(
            self.run_id, digest, redact_text(canonical_request(messages))
        )
        return digest

    def next_block_id(self) -> str:
        self._blocks += 1
        return f"block-{self._blocks:06d}"

    def next_call_id(self) -> str:
        self._calls += 1
        return f"call-{self._calls:06d}"

    def answered(
        self, call_id: str, messages: tuple[Message, ...], answer: str
    ) -> None:
        """Remember request plus answer, the prefix a later turn extends."""
        self._continuations[continuation_hash(messages, answer)] = call_id

    def parent_of(
        self, messages: tuple[Message, ...]
    ) -> tuple[str | None, str | None]:
        """The call whose request plus answer is the longest prefix, and its hash."""
        for length in range(len(messages) - 1, 0, -1):
            digest = request_hash(messages[:length])
            if digest in self._continuations:
                return self._continuations[digest], digest
        return None, None

    def wrap(
        self, client: object, block_id: str | None = None
    ) -> "RecordingModelClient":
        """One wrapped client is one block; ``block_id`` continues a recorded one."""
        return RecordingModelClient(client, self, block_id)


class RecordingModelClient:
    """Emit RequestSent, then one outcome event, for every attempt.

    The outcome is ResponseReceived, RequestFailed, or AttemptInterrupted
    when the inner client raises. ``attempt == 1`` starts a new logical call;
    a retrying client sets higher attempts for the same call.
    """

    def __init__(
        self, inner: object, session: RunSession, block_id: str | None = None
    ) -> None:
        self._inner = inner
        self._session = session
        self.stage: str | None = None
        self.cell_identity: str | None = None
        self.scenario_id: str | None = None
        self.verification_report_ids: tuple[str, ...] = ()
        self.attempt: int = 1
        self.block_id = block_id or session.next_block_id()
        self.call_id: str | None = None
        self._parent: tuple[str | None, str | None] = (None, None)
        self._offset = 0
        self._resumed: tuple[str, int] | None = None

    def resume_call(self, call_id: str, recorded_attempts: int) -> None:
        """Continue a recorded call: its next attempts are numbered after these."""
        self._resumed = (call_id, recorded_attempts)

    def label(
        self, stage: str | None, cell_identity: str | None, scenario_id: str
    ) -> None:
        """Name the stage, cell and item of the next logical call, set by the runner."""
        self.stage = stage
        self.cell_identity = cell_identity
        self.scenario_id = scenario_id

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        session = self._session
        if self._resumed is not None and self.attempt == 1:
            self.call_id, self._offset = self._resumed
            self._resumed = None
            self._parent = session.parent_of(messages)
        elif self.attempt == 1 or self.call_id is None:
            self.call_id = session.next_call_id()
            self._offset = 0
            self._parent = session.parent_of(messages)
        call_id = self.call_id
        attempt = self.attempt + self._offset
        parent_call_id, prefix_hash = self._parent
        digest = session.save_request(messages)
        request_sequence = session.sink.next_sequence
        session.sink.emit(
            RequestSent(
                sequence=session.sink.next_sequence,
                run_id=session.run_id,
                occurred_at=session._now(),
                requested_message_count=len(messages),
                requested_model=session.requested_model,
                requested_endpoint=session.requested_endpoint,
                request_hash=digest,
                attempt=attempt,
                call_id=call_id,
                block_id=self.block_id,
                parent_call_id=parent_call_id,
                prefix_hash=prefix_hash,
                stage=self.stage,
                cell_identity=self.cell_identity,
                scenario_id=self.scenario_id,
                verification_report_ids=self.verification_report_ids,
            )
        )
        try:
            result: ModelResult = self._inner.complete(messages)  # type: ignore[attr-defined]
        except BaseException as exc:
            session.sink.emit(
                AttemptInterrupted(
                    sequence=session.sink.next_sequence,
                    run_id=session.run_id,
                    occurred_at=session._now(),
                    call_id=call_id,
                    attempt=attempt,
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
            raise
        evidence: CallEvidence | None = getattr(self._inner, "last_evidence", None)
        observed = self._observed(evidence, request_sequence)
        failure = failure_class(result)
        if failure is None:
            assert isinstance(result, AnswerSuccess)
            session.sink.emit(
                ResponseReceived(
                    sequence=session.sink.next_sequence,
                    run_id=session.run_id,
                    occurred_at=session._now(),
                    call_id=call_id,
                    raw_response=result.raw_response,
                    observed_message_count=result.observed_message_count,
                    attempt=attempt,
                    verification_report_ids=self.verification_report_ids,
                    **observed,
                )
            )
            session.answered(call_id, messages, result.response.answer)
        else:
            session.sink.emit(
                RequestFailed(
                    sequence=session.sink.next_sequence,
                    run_id=session.run_id,
                    occurred_at=session._now(),
                    call_id=call_id,
                    failure=failure,
                    detail=getattr(result, "detail", failure.value),
                    raw_response=getattr(result, "raw_response", None),
                    attempt=attempt,
                    **observed,
                )
            )
        return result

    def _observed(
        self, evidence: CallEvidence | None, request_sequence: int
    ) -> _Observed:
        """Observed fields from evidence; empty without it."""
        if evidence is None:
            return {}
        ref = f"request-{request_sequence:06d}"
        digest = self._session.write_envelope(ref, evidence.model_dump_json(indent=2))
        return {
            "envelope_hash": digest,
            "observed_model": evidence.observed_model,
            "observed_endpoint": evidence.observed_endpoint,
            "observed_snapshot": evidence.observed_snapshot,
            "cache_status": evidence.cache_status,
            "generation_id": evidence.generation_id,
            "finish_reason": evidence.finish_reason,
            "usage": evidence.usage,
            "envelope_ref": ref,
        }


def maybe_wrap(
    client: object,
    sink: object | None,
) -> object:
    """Keep existing runners working when no durable sink is supplied."""
    if sink is None or isinstance(sink, NullSink):
        return client
    return sink

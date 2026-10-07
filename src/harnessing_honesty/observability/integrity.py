"""Check a run directory against itself and name each integrity failure.

Each check reads the loaded events and yields issues; none shares state. An
interrupted history is not a failure: attempts without outcomes are reported
by ``ReconstructedRun.attempts``.
"""

from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from harnessing_honesty.domain.enums import RecordStatus
from harnessing_honesty.domain.events import (
    AttemptInterrupted,
    DomainEvent,
    RequestFailed,
    RequestSent,
    ResponseReceived,
    RunClosed,
)
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.records import RunRecord
from harnessing_honesty.domain.responses import normalize_binary_answer
from harnessing_honesty.observability.hashing import (
    continuation_hash,
    digest_text,
    request_hash,
)
from harnessing_honesty.observability.reconstruct import saved_request

_EVENT_ADAPTER = TypeAdapter(DomainEvent)
_OUTCOMES = (ResponseReceived, RequestFailed, AttemptInterrupted)


class Integrity(StrEnum):
    MISSING_FILE = "missing_file"
    UNREADABLE = "unreadable"
    SEQUENCE = "sequence"
    RUN_ID = "run_id"
    SUMMARY = "summary"
    MISLINKED_OUTCOME = "mislinked_outcome"
    DUPLICATE_ATTEMPT = "duplicate_attempt"
    REQUEST_HASH = "request_hash"
    ENVELOPE_HASH = "envelope_hash"
    BROKEN_LINEAGE = "broken_lineage"
    MIXED_BLOCK = "mixed_block"
    UNREFERENCED_FILE = "unreferenced_file"


class IntegrityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Integrity
    where: str
    detail: str


class IntegrityError(ValueError):
    """Raised by reconstruction when a run directory fails its checks."""

    def __init__(self, issues: tuple[IntegrityIssue, ...]) -> None:
        self.issues = issues
        super().__init__(
            "; ".join(f"{i.kind.value} at {i.where}: {i.detail}" for i in issues)
        )


def require_integrity(run_dir: Path) -> None:
    issues = check_integrity(run_dir)
    if issues:
        raise IntegrityError(issues)


def check_integrity(run_dir: Path) -> tuple[IntegrityIssue, ...]:
    """Every failure found, cause before consequence. Empty means consistent."""
    record, summary_issues = _read_summary(run_dir)
    events, event_issues = _read_events(run_dir)
    if events is None:
        return summary_issues + event_issues
    return (
        *summary_issues,
        *event_issues,
        *_order_issues(events, record),
        *_attempt_issues(events),
        *_file_issues(run_dir, events),
        *_lineage_issues(run_dir, events),
        *_block_issues(events),
    )


def _issue(kind: Integrity, where: str, detail: str) -> IntegrityIssue:
    return IntegrityIssue(kind=kind, where=where, detail=detail)


def _read_summary(run_dir: Path) -> tuple[RunRecord | None, tuple[IntegrityIssue, ...]]:
    path = run_dir / "summary.json"
    if not path.exists():
        return None, (_issue(Integrity.MISSING_FILE, "summary.json", "absent"),)
    try:
        return RunRecord.model_validate_json(path.read_text(encoding="utf-8")), ()
    except ValidationError as exc:
        detail = exc.errors()[0]["msg"]
        return None, (_issue(Integrity.UNREADABLE, "summary.json", detail),)


def _read_events(
    run_dir: Path,
) -> tuple[list[DomainEvent] | None, tuple[IntegrityIssue, ...]]:
    path = run_dir / "events.jsonl"
    if not path.exists():
        return None, (_issue(Integrity.MISSING_FILE, "events.jsonl", "absent"),)
    events: list[DomainEvent] = []
    issues: list[IntegrityIssue] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            events.append(_EVENT_ADAPTER.validate_json(line))
        except ValidationError as exc:
            where = f"events.jsonl:{number}"
            issues.append(_issue(Integrity.UNREADABLE, where, exc.errors()[0]["msg"]))
    return events, tuple(issues)


def _order_issues(
    events: list[DomainEvent], record: RunRecord | None
) -> Iterator[IntegrityIssue]:
    """Dense sequence, one run id, and a summary the events support."""
    gaps = (i for i, event in enumerate(events) if event.sequence != i)
    first_gap = next(gaps, None)
    if first_gap is not None:
        detail = f"has sequence {events[first_gap].sequence}"
        yield _issue(Integrity.SEQUENCE, f"event {first_gap}", detail)
    run_id = record.run_id if record else (events[0].run_id if events else None)
    for event in events:
        if event.run_id != run_id:
            detail = f"run_id {event.run_id!r}"
            yield _issue(Integrity.RUN_ID, f"event {event.sequence}", detail)
    if record is None or record.status is RecordStatus.INCOMPLETE:
        return
    closed = [event.status for event in events if isinstance(event, RunClosed)]
    if not closed or closed[-1] is not record.status:
        found = closed[-1] if closed else "no run_closed event"
        detail = f"says {record.status}; events show {found}"
        yield _issue(Integrity.SUMMARY, "summary.json", detail)


def _answers(
    request: DomainEvent | None,
    outcome: ResponseReceived | RequestFailed | AttemptInterrupted,
) -> bool:
    """Dispatch is sequential: an outcome directly follows its own request."""
    return isinstance(request, RequestSent) and (
        (request.call_id, request.attempt) == (outcome.call_id, outcome.attempt)
    )


def _attempt_issues(events: list[DomainEvent]) -> Iterator[IntegrityIssue]:
    seen: set[tuple[str, int]] = set()
    for previous, event in zip([None, *events], events):
        where = f"event {event.sequence}"
        if isinstance(event, RequestSent) and event.call_id is not None:
            key = (event.call_id, event.attempt)
            if key in seen:
                yield _issue(Integrity.DUPLICATE_ATTEMPT, where, f"{key} repeated")
            seen.add(key)
        if isinstance(event, _OUTCOMES) and not _answers(previous, event):
            detail = f"no request for {(event.call_id, event.attempt)}"
            yield _issue(Integrity.MISLINKED_OUTCOME, where, detail)


def _file_issues(run_dir: Path, events: list[DomainEvent]) -> Iterator[IntegrityIssue]:
    """Referenced files exist and match their hashes; nothing else is present.

    An envelope is named after its request's sequence, so one written just
    before a crash, with no outcome event, still belongs to the run.
    """
    expected: dict[str, tuple[str | None, Integrity]] = {}
    belongs: set[str] = set()
    for event in events:
        if isinstance(event, RequestSent):
            belongs.add(f"envelopes/request-{event.sequence:06d}.json")
            if event.call_id is not None and event.request_hash is not None:
                name = f"requests/{event.request_hash}.json"
                expected[name] = (event.request_hash, Integrity.REQUEST_HASH)
        elif isinstance(event, ResponseReceived | RequestFailed) and event.envelope_ref:
            name = f"envelopes/{event.envelope_ref}.json"
            expected[name] = (event.envelope_hash, Integrity.ENVELOPE_HASH)
    for name, (digest, kind) in expected.items():
        path = run_dir / name
        if not path.exists():
            yield _issue(Integrity.MISSING_FILE, name, "absent")
        elif digest is not None and digest_text(path.read_text(encoding="utf-8")) != digest:
            yield _issue(kind, name, "content does not match its recorded hash")
    for folder in ("requests", "envelopes"):
        directory = run_dir / folder
        present = sorted(directory.iterdir()) if directory.is_dir() else []
        for path in present:
            name = f"{folder}/{path.name}"
            # An interrupted atomic write leaves its .tmp; the target is absent.
            if name not in expected and name not in belongs and path.suffix != ".tmp":
                yield _issue(Integrity.UNREFERENCED_FILE, name, "no event refers to it")


def _lineage_issues(
    run_dir: Path, events: list[DomainEvent]
) -> Iterator[IntegrityIssue]:
    """Each parent answered earlier; its request plus answer prefixes the child."""
    answered: dict[str, tuple[str, int]] = {}
    for request, outcome in zip(events, [*events[1:], None]):
        if not isinstance(request, RequestSent) or request.call_id is None:
            continue
        messages = _messages(run_dir, request.request_hash)
        if request.parent_call_id is not None:
            yield from _parent_issues(request, messages, answered)
        if not isinstance(outcome, ResponseReceived) or not _answers(request, outcome):
            continue
        answer = normalize_binary_answer(outcome.raw_response or "")
        if answer is not None and messages is not None:
            prefix = (continuation_hash(messages, answer), len(messages) + 1)
            answered[request.call_id] = prefix


def _parent_issues(
    request: RequestSent,
    messages: tuple[Message, ...] | None,
    answered: dict[str, tuple[str, int]],
) -> Iterator[IntegrityIssue]:
    where = f"event {request.sequence}"
    parent = answered.get(str(request.parent_call_id))
    if parent is None:
        detail = f"parent {request.parent_call_id} has no earlier answer"
        yield _issue(Integrity.BROKEN_LINEAGE, where, detail)
        return
    digest, length = parent
    extends = messages is None or request_hash(messages[:length]) == digest
    if digest != request.prefix_hash or not extends:
        detail = f"does not extend {request.parent_call_id}"
        yield _issue(Integrity.BROKEN_LINEAGE, where, detail)


def _block_issues(events: list[DomainEvent]) -> Iterator[IntegrityIssue]:
    """One block is one item; a block naming two items would misattribute rows."""
    items: dict[str, set[str | None]] = {}
    for event in events:
        if isinstance(event, RequestSent) and event.block_id is not None:
            items.setdefault(event.block_id, set()).add(event.scenario_id)
    for block_id, found in items.items():
        if len(found) > 1:
            detail = f"names items {sorted(map(str, found))}"
            yield _issue(Integrity.MIXED_BLOCK, block_id, detail)


def _messages(run_dir: Path, digest: str | None) -> tuple[Message, ...] | None:
    """Saved messages, or ``None`` when absent or unreadable (reported elsewhere)."""
    if digest is None or not (run_dir / "requests" / f"{digest}.json").exists():
        return None
    try:
        return saved_request(run_dir, digest)
    except ValidationError:
        return None

"""Corruption matrix: each damaged artifact is named by its integrity failure."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from harnessing_honesty.analysis.reconstruct import require_closed_matrix
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess
from harnessing_honesty.domain.evidence import CallEvidence
from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.integrity import (
    Integrity,
    IntegrityError,
    check_integrity,
)
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore
from harnessing_honesty.runtime.episode import run_development_matrix

FIXTURE = development_fixture()


class _WithEvidence(ScriptedModelClient):
    """Exposes empty transport evidence, so every attempt writes an envelope."""

    last_evidence = CallEvidence(exchanges=())


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    answer = AnswerSuccess(
        response=AnswerResponse(answer=FIXTURE.correct_answer),
        raw_response=FIXTURE.correct_answer,
        requested_message_count=1,
    )
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    session.start()
    run_development_matrix(FIXTURE.prompt, _WithEvidence([answer] * 13), 0, session=session)
    session.close()
    return store.run_dir("run-1")


def _events(run_dir: Path) -> list[dict]:
    path = run_dir / "events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_events(run_dir: Path, events: list[dict]) -> None:
    lines = [json.dumps(event, separators=(",", ":")) for event in events]
    (run_dir / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _edit_events(change: Callable[[list[dict]], None]) -> Callable[[Path], None]:
    def apply(run_dir: Path) -> None:
        events = _events(run_dir)
        change(events)
        _write_events(run_dir, events)

    return apply


def _last(kind: str) -> Callable[[list[dict]], dict]:
    return lambda events: [e for e in events if e["kind"] == kind][-1]


def _leaf_request(run_dir: Path) -> Path:
    return run_dir / "requests" / f"{_last('request_sent')(_events(run_dir))['request_hash']}.json"


def _envelope(run_dir: Path) -> Path:
    return run_dir / "envelopes" / "request-000001.json"


def _append(path: Path) -> None:
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")


def _misspell_kind(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("response_received", "response_recieved", 1), encoding="utf-8")


def _relink_outcome(events: list[dict]) -> None:
    _last("response_received")(events)["call_id"] = "call-000001"


def _repeat_call(events: list[dict]) -> None:
    request, outcome = events[-3], events[-2]
    request["call_id"] = outcome["call_id"] = events[-5]["call_id"]


def _reparent(events: list[dict]) -> None:
    request = _last("request_sent")(events)
    request["parent_call_id"] = "call-000001"


def _swap(events: list[dict]) -> None:
    events[3], events[4] = events[4], events[3]


def _claim_complete_without_close(run_dir: Path) -> None:
    _write_events(run_dir, _events(run_dir)[:-1])


CORRUPTIONS: list[tuple[str, Callable[[Path], None], Integrity]] = [
    ("deleted events", lambda d: (d / "events.jsonl").unlink(), Integrity.MISSING_FILE),
    ("deleted summary", lambda d: (d / "summary.json").unlink(), Integrity.MISSING_FILE),
    ("deleted request", lambda d: _leaf_request(d).unlink(), Integrity.MISSING_FILE),
    ("deleted envelope", lambda d: _envelope(d).unlink(), Integrity.MISSING_FILE),
    ("altered request", lambda d: _append(_leaf_request(d)), Integrity.REQUEST_HASH),
    ("altered envelope", lambda d: _append(_envelope(d)), Integrity.ENVELOPE_HASH),
    ("altered event line", lambda d: _misspell_kind(d / "events.jsonl"), Integrity.UNREADABLE),
    ("duplicated event", _edit_events(lambda e: e.insert(2, e[1])), Integrity.SEQUENCE),
    ("reordered events", _edit_events(_swap), Integrity.SEQUENCE),
    ("foreign run id", _edit_events(lambda e: e[2].update(run_id="other")), Integrity.RUN_ID),
    ("closed summary, open run", _claim_complete_without_close, Integrity.SUMMARY),
    ("mislinked outcome", _edit_events(_relink_outcome), Integrity.MISLINKED_OUTCOME),
    ("duplicated attempt", _edit_events(_repeat_call), Integrity.DUPLICATE_ATTEMPT),
    ("mislinked parent", _edit_events(_reparent), Integrity.BROKEN_LINEAGE),
    ("stray request", lambda d: (d / "requests" / "x.json").write_text("[]"), Integrity.UNREFERENCED_FILE),
]


def test_an_untouched_run_has_no_issues(run_dir: Path) -> None:
    assert check_integrity(run_dir) == ()
    assert len(require_closed_matrix(run_dir).branches) == 9


@pytest.mark.parametrize(
    ("corrupt", "expected"),
    [(c, e) for _, c, e in CORRUPTIONS],
    ids=[name for name, _, _ in CORRUPTIONS],
)
def test_each_corruption_is_named(
    run_dir: Path, corrupt: Callable[[Path], None], expected: Integrity
) -> None:
    corrupt(run_dir)

    issues = check_integrity(run_dir)

    assert issues
    assert issues[0].kind is expected
    with pytest.raises(IntegrityError) as raised:
        require_closed_matrix(run_dir)
    assert raised.value.issues == issues


def test_an_interrupted_history_is_not_corruption(run_dir: Path) -> None:
    events = _events(run_dir)[:-2]
    _write_events(run_dir, events)
    summary = run_dir / "summary.json"
    summary.write_text(
        summary.read_text(encoding="utf-8").replace('"complete"', '"incomplete"'),
        encoding="utf-8",
    )

    rebuilt = reconstruct_run(run_dir)

    assert check_integrity(run_dir) == ()
    assert rebuilt.interrupted
    assert rebuilt.attempts[-1].outcome == "no_outcome"

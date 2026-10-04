"""Call identities, parent links, intent before dispatch, indeterminate attempts."""

import json
from pathlib import Path

import pytest

from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.domain.enums import Failure, RecordStatus
from harnessing_honesty.domain.events import RequestSent, ResponseReceived
from harnessing_honesty.domain.results import ModelResult, ParseFailure
from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.retries import RetryingClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.hashing import digest_text, request_hash
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore
from harnessing_honesty.runtime.episode import run_development_matrix

REQUEST = (Message(role="user", content="Does the claim follow?"),)


def _success(answer: str, count: int = 1) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(answer=answer),
        raw_response=f" {answer.upper()}\n",
        requested_message_count=count,
    )


def _session(tmp_path: Path) -> tuple[FilesystemRecordStore, RunSession]:
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    session.start()
    return store, session


def test_matrix_calls_link_to_the_prefix_they_extend(tmp_path: Path) -> None:
    fixture = development_fixture()
    counts = (1,) + (3,) * 3 + (5,) * 9
    client = ScriptedModelClient(
        [_success(fixture.correct_answer, count) for count in counts]
    )
    store, session = _session(tmp_path)

    run_development_matrix(fixture.prompt, client, 0, session=session)
    session.close()
    rebuilt = reconstruct_run(store.run_dir("run-1"))
    sent = [event for event in rebuilt.events if isinstance(event, RequestSent)]

    assert [event.call_id for event in sent] == [f"call-{n:06d}" for n in range(1, 14)]
    assert {event.block_id for event in sent} == {"block-000001"}
    neutral = sent[0]
    drafts = [event for event in sent if event.requested_message_count == 3]
    finals = [event for event in sent[1:] if event not in drafts]
    assert (len(drafts), len(finals)) == (3, 9)
    assert neutral.parent_call_id is None
    assert {draft.parent_call_id for draft in drafts} == {neutral.call_id}
    for draft in drafts:
        children = [final for final in finals if final.parent_call_id == draft.call_id]
        assert len(children) == 3
    answer = Message(role="assistant", content=fixture.correct_answer)
    requests = dict(zip((e.call_id for e in sent), client.requests, strict=True))
    for event in sent:
        assert event.request_hash == request_hash(requests[event.call_id])
        if event.parent_call_id is not None:
            parent = requests[event.parent_call_id]
            assert event.prefix_hash == request_hash(parent + (answer,))
    assert all(attempt.outcome == "answered" for attempt in rebuilt.attempts)


def test_the_request_is_saved_before_dispatch(tmp_path: Path) -> None:
    store, session = _session(tmp_path)
    digest = request_hash(REQUEST)
    seen: list[tuple[bool, str]] = []

    class Inspecting:
        def complete(self, messages: tuple[Message, ...]) -> ModelResult:
            saved = store.requests_dir("run-1") / f"{digest}.json"
            last = store.events_path("run-1").read_text(encoding="utf-8").splitlines()[-1]
            seen.append((saved.exists(), json.loads(last)["kind"]))
            return _success("yes")

    session.wrap(Inspecting()).complete(REQUEST)
    saved = (store.requests_dir("run-1") / f"{digest}.json").read_text(encoding="utf-8")

    assert seen == [(True, "request_sent")]
    assert digest_text(saved) == digest
    assert [Message.model_validate(item) for item in json.loads(saved)] == list(REQUEST)


def test_the_raw_answer_text_is_kept(tmp_path: Path) -> None:
    store, session = _session(tmp_path)

    session.wrap(ScriptedModelClient([_success("no")])).complete(REQUEST)
    received = [
        event
        for event in reconstruct_run(store.run_dir("run-1")).events
        if isinstance(event, ResponseReceived)
    ]

    assert [event.raw_response for event in received] == [" NO\n"]


def test_retries_share_a_call_and_the_next_call_is_new(tmp_path: Path) -> None:
    store, session = _session(tmp_path)
    parse = ParseFailure(detail="not yes or no", raw_response="Yes, it follows.")
    inner = session.wrap(ScriptedModelClient([parse, _success("yes"), _success("no")]))
    client = RetryingClient(inner, clock=FakeClock())

    client.complete(REQUEST)
    client.complete(REQUEST)
    attempts = reconstruct_run(store.run_dir("run-1")).attempts

    assert [(a.call_id, a.attempt, a.outcome, a.failure) for a in attempts] == [
        ("call-000001", 1, "failed", Failure.PARSE),
        ("call-000001", 2, "answered", None),
        ("call-000002", 1, "answered", None),
    ]
    assert len(list(store.requests_dir("run-1").iterdir())) == 1


def test_an_exception_during_dispatch_is_recorded_as_interrupted(tmp_path: Path) -> None:
    store, session = _session(tmp_path)

    class Raising:
        def complete(self, messages: tuple[Message, ...]) -> ModelResult:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        session.wrap(Raising()).complete(REQUEST)
    rebuilt = reconstruct_run(store.run_dir("run-1"))

    assert rebuilt.events[-1].kind == "attempt_interrupted"
    assert [(a.outcome, a.indeterminate) for a in rebuilt.attempts] == [
        ("interrupted", True)
    ]
    assert rebuilt.record.status is RecordStatus.INCOMPLETE


def test_a_request_with_no_outcome_is_indeterminate(tmp_path: Path) -> None:
    store, session = _session(tmp_path)
    session.wrap(ScriptedModelClient([_success("yes")])).complete(REQUEST)
    path = store.events_path("run-1")
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    attempts = reconstruct_run(store.run_dir("run-1")).attempts

    assert [(a.outcome, a.indeterminate) for a in attempts] == [("no_outcome", True)]


def test_an_outcome_for_another_call_is_a_lineage_error(tmp_path: Path) -> None:
    store, session = _session(tmp_path)
    session.wrap(ScriptedModelClient([_success("yes")])).complete(REQUEST)
    path = store.events_path("run-1")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines[-1] = lines[-1].replace('"call-000001"', '"call-000009"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match request"):
        reconstruct_run(store.run_dir("run-1")).attempts


def test_envelopes_and_requests_are_written_once(tmp_path: Path) -> None:
    store = FilesystemRecordStore(tmp_path)
    store.create("run-1")

    store.write_envelope("run-1", "request-000001", "{}")
    store.write_request("run-1", "abc", "[]")
    store.write_request("run-1", "abc", "[]")

    with pytest.raises(FileExistsError):
        store.write_envelope("run-1", "request-000001", "{}")
    with pytest.raises(FileExistsError):
        store.write_request("run-1", "abc", "[1]")
    assert not list(store.run_dir("run-1").rglob("*.tmp"))

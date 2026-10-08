"""A final event line cut short by an interruption is set aside, not read."""

from pathlib import Path

import pytest

from harnessing_honesty.domain import AnswerResponse, AnswerSuccess
from harnessing_honesty.domain.events import RunResumed
from harnessing_honesty.evaluation.collection import collection_status
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.integrity import check_integrity
from harnessing_honesty.observability.reconstruct import event_lines, reconstruct_run
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore, set_aside_tail

from tests.evaluation.test_collection_resume import _execute, _interrupted, _runs
from tests.development import development_fixture, run_development_matrix

# Cut inside a JSON line and inside the two-byte "é", as a kill mid-write can.
FRAGMENT = '{"kind":"response_received","raw_response":"ré'.encode()[:-1]


def _matrix_run(root: Path) -> Path:
    fixture = development_fixture()
    answer = AnswerSuccess(
        response=AnswerResponse.model_validate({"answer": fixture.correct_answer}),
        raw_response=fixture.correct_answer,
        requested_message_count=1,
    )
    store = FilesystemRecordStore(root)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    session.start()
    client = ScriptedModelClient([answer] * 13)
    run_development_matrix(fixture.prompt, client, 0, session=session)
    return store.run_dir("run-1")


def test_lines_without_their_newline_are_not_events() -> None:
    assert event_lines(b"") == ([], None)
    assert event_lines(b'{"a":1}\r\n') == (['{"a":1}'], None)
    # Even a line that parses is unfinished until its newline was written.
    assert event_lines(b'{"a":1}\n{"b":2}') == (['{"a":1}'], b'{"b":2}')


def test_integrity_and_reconstruction_ignore_an_unfinished_line(tmp_path: Path) -> None:
    run_dir = _matrix_run(tmp_path)
    before = reconstruct_run(run_dir).events
    with (run_dir / "events.jsonl").open("ab") as handle:
        handle.write(FRAGMENT)

    rebuilt = reconstruct_run(run_dir)

    assert check_integrity(run_dir) == ()
    assert rebuilt.events == before
    assert rebuilt.unfinished_tail is not None


def test_setting_aside_keeps_the_bytes_and_can_be_repeated(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    events.write_bytes(b'{"a":1}\n' + FRAGMENT)

    set_aside_tail(events, "events-unfinished-000001.txt")
    set_aside_tail(events, "events-unfinished-000001.txt")

    assert events.read_bytes() == b'{"a":1}\n'
    assert (tmp_path / "events-unfinished-000001.txt").read_bytes() == FRAGMENT
    events.write_bytes(b'{"a":1}\nother')
    with pytest.raises(FileExistsError):
        set_aside_tail(events, "events-unfinished-000001.txt")


def test_a_collection_cut_mid_write_resumes(tmp_path: Path) -> None:
    spec, directory = _interrupted(tmp_path)
    run_dir = next(run for run in _runs(tmp_path, spec) if run.exists())
    original = (run_dir / "events.jsonl").read_bytes()
    with (run_dir / "events.jsonl").open("ab") as handle:
        handle.write(FRAGMENT)
    assert not collection_status(directory).complete

    _execute(directory, spec, [])

    assert collection_status(directory).complete
    events = reconstruct_run(run_dir).events
    assert (run_dir / "events.jsonl").read_bytes().startswith(original)
    resumed = [event for event in events if isinstance(event, RunResumed)]
    name = f"events-unfinished-{len(original.splitlines()):06d}.txt"
    assert [event.unfinished_tail for event in resumed] == [name]
    assert (run_dir / name).read_bytes() == FRAGMENT
    others = [run for run in _runs(tmp_path, spec) if run != run_dir]
    for other in others:
        tails = [e.unfinished_tail for e in reconstruct_run(other).events
                 if isinstance(e, RunResumed)]
        assert tails == [None]

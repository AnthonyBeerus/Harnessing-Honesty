"""The run-audit notebook source runs offline against a recorded fixture run."""

from pathlib import Path

import pytest

from harnessing_honesty.domain import AnswerResponse, AnswerSuccess
from harnessing_honesty.domain.results import ParseFailure
from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.retries import RetryingClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore
from harnessing_honesty.runtime.episode import run_development_matrix, run_episode

SOURCE = Path(__file__).resolve().parents[2] / "notebooks" / "02_run_audit.py"


def _run_notebook(run_directory: Path | None) -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert source.count("run_directory = None") == 1
    if run_directory is not None:
        selected = f"run_directory = Path({str(run_directory)!r})"
        source = source.replace("run_directory = None", selected)
    exec(compile(source, str(SOURCE), "exec"), {"__name__": "__main__"})


def test_with_no_run_selected_nothing_is_read(capsys: pytest.CaptureFixture[str]) -> None:
    _run_notebook(None)

    assert capsys.readouterr().out == "No run selected. No audit results are available.\n"


def test_a_recorded_matrix_is_audited(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = development_fixture()
    answer = AnswerSuccess(
        response=AnswerResponse(answer=fixture.correct_answer),
        raw_response=fixture.correct_answer,
        requested_message_count=1,
    )
    parse = ParseFailure(detail="not yes or no", raw_response="Probably.")
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    session.start()
    inner = session.wrap(ScriptedModelClient([parse] + [answer] * 13))
    run_development_matrix(fixture.prompt, RetryingClient(inner, clock=FakeClock()), 0)
    session.close()

    _run_notebook(store.run_dir("run-1"))
    out = capsys.readouterr().out

    assert "Logical calls: 13; attempts: 14" in out
    assert "Indeterminate attempts: 0" in out
    assert "0 integrity issues" in out
    assert "call-000001 #1 block-000001 neutral None parse parent=None" in out
    assert "0 parse discrepancies" in out
    assert "Matrix drafts present: 3 of 3; finals present: 9 of 9" in out


def test_a_recorded_answer_that_does_not_parse_is_a_discrepancy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mislabelled = AnswerSuccess(
        response=AnswerResponse(answer="yes"),
        raw_response="Yes, probably.",
        requested_message_count=1,
    )
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    run_episode(development_fixture().prompt, ScriptedModelClient([mislabelled]), session)
    session.close()

    _run_notebook(store.run_dir("run-1"))
    out = capsys.readouterr().out

    assert "parse discrepancy: call-000001 #1 answered 'Yes, probably.'" in out
    assert "No matrix rebuilt: integrity issues or no stage labels." in out

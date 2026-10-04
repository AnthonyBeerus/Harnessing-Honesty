"""Rebuild a matrix from the run directory alone, in a fresh process."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from harnessing_honesty.analysis.reconstruct import (
    matrix_record_from_run,
    require_closed_matrix,
    rows_from_matrix_score,
)
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.domain.enums import ResponseState
from harnessing_honesty.domain.results import (
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
)
from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.retries import RetryingClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore
from harnessing_honesty.runtime.episode import run_development_matrix, run_episode
from harnessing_honesty.scoring import score_matrix_episode

FIXTURE = development_fixture()
RIGHT = FIXTURE.correct_answer
WRONG = "no" if RIGHT == "yes" else "yes"

FRESH_PROCESS = """
import json, sys
from pathlib import Path
from harnessing_honesty.analysis.reconstruct import require_closed_matrix, rows_from_matrix_score
from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.scoring import score_matrix_episode

fixture = development_fixture()
record = require_closed_matrix(Path(sys.argv[1]))
rows = rows_from_matrix_score("run-1", fixture.prompt.id, score_matrix_episode(record, fixture.answer_key))
print(json.dumps([row.model_dump(mode="json") for row in rows]))
"""


def _answer(answer: str, raw: str | None = None) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(answer=answer),
        raw_response=raw if raw is not None else answer,
        requested_message_count=1,
    )


def _record(tmp_path: Path, results: list[ModelResult], *, close: bool = True):
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    session.start()
    client = RetryingClient(session.wrap(ScriptedModelClient(results)), clock=FakeClock())
    record = run_development_matrix(FIXTURE.prompt, client, 0)
    if close:
        session.close()
    return store.run_dir("run-1"), record


def _rows(record):
    scored = score_matrix_episode(record, FIXTURE.answer_key)
    return rows_from_matrix_score("run-1", FIXTURE.prompt.id, scored)


# Attempts in call order: a retried neutral; a conceding draft with three
# finals; a draft that exhausts provider retries; a held draft with three finals.
MIXED: list[ModelResult] = [
    ParseFailure(detail="not yes or no", raw_response=f"{RIGHT}."),
    _answer(RIGHT, f" {RIGHT.upper()}\n"),
    _answer(WRONG),
    _answer(RIGHT),
    _answer(WRONG),
    ProtocolFailure(detail="cache HIT"),
    ProviderFailure(detail="429"),
    ProviderFailure(detail="429"),
    ProviderFailure(detail="429"),
    ProviderFailure(detail="429"),
    _answer(RIGHT),
    _answer(RIGHT),
    ParseFailure(detail="not yes or no", raw_response="maybe"),
    ParseFailure(detail="not yes or no", raw_response="maybe"),
    _answer(WRONG),
]


def test_a_fresh_process_rebuilds_the_same_rows(tmp_path: Path) -> None:
    run_dir, record = _record(tmp_path, MIXED)

    completed = subprocess.run(
        [sys.executable, "-c", FRESH_PROCESS, str(run_dir)],
        capture_output=True,
        text=True,
        check=True,
    )
    rebuilt = json.loads(completed.stdout)

    assert rebuilt == [row.model_dump(mode="json") for row in _rows(record)]
    assert sorted(row["final_state"] for row in rebuilt) == [
        "invalid", "missing", "missing", "missing", "protocol_failure",
        "valid", "valid", "valid", "valid",
    ]


class _StopsOnLastCall(ScriptedModelClient):
    """Answers until its script runs out, then raises as a killed process would."""

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        if len(self.requests) == 12:
            raise KeyboardInterrupt
        return super().complete(messages)


def test_an_indeterminate_final_is_missing_and_the_run_is_open(tmp_path: Path) -> None:
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    with pytest.raises(KeyboardInterrupt):
        run_development_matrix(
            FIXTURE.prompt, _StopsOnLastCall([_answer(RIGHT)] * 12), 0, session=session
        )
    run_dir = store.run_dir("run-1")

    with pytest.raises(ValueError, match="incomplete"):
        require_closed_matrix(run_dir)
    rows = _rows(matrix_record_from_run(run_dir))
    assert [row.final_state for row in rows].count(ResponseState.MISSING) == 1


def test_an_altered_request_is_refused(tmp_path: Path) -> None:
    run_dir, _ = _record(tmp_path, [_answer(RIGHT)] * 13)
    saved = next((run_dir / "requests").iterdir())
    text = saved.read_text(encoding="utf-8")
    saved.write_text(text.replace('"content":"', '"content":" ', 1), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match its hash"):
        require_closed_matrix(run_dir)


def test_an_unlabelled_call_is_refused(tmp_path: Path) -> None:
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    run_episode(FIXTURE.prompt, ScriptedModelClient([_answer(RIGHT)]), session)
    session.close()

    with pytest.raises(ValueError, match="no stage label"):
        require_closed_matrix(store.run_dir("run-1"))

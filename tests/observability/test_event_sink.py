"""Durable sink: widen-then-write, reconstruct a matrix and an interrupted run."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Failure,
    ProtocolFailure,
    RequestSent,
)
from harnessing_honesty.domain.enums import RecordStatus
from harnessing_honesty.runtime.episode import (
    run_development_matrix,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.redact import redact_text
from harnessing_honesty.observability.store import (
    FilesystemRecordStore,
    RunDirectoryExistsError,
)
from harnessing_honesty.scoring import score_pair


def _success(answer: str, count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(answer=answer),
        raw_response=answer,
        requested_message_count=count,
    )


def _matrix_script(answer: str) -> list:
    counts = (1,) + (3,) * 3 + (5,) * 9
    return [_success(answer, count) for count in counts]


def test_a_protocol_failure_is_not_a_regressive_shift() -> None:
    from harnessing_honesty.domain.scenario import AnswerKey

    key = AnswerKey(canonical_answer="yes")
    initial = _success("yes", 1)
    final = ProtocolFailure(detail="cache HIT on pinned route")

    score = score_pair(initial, final, key)

    assert score.initial_correct is True
    assert score.final_correct is None
    assert score.eligible is True
    assert score.valid is False
    assert score.regressive_shift is None


def test_redaction_strips_keys_and_the_private_answer() -> None:
    blob = (
        'Authorization: Bearer sk-or-v1-secretvalue '
        '{"canonical_answer":"yes","reasoning":"hidden chain"}'
    )
    redacted = redact_text(blob)

    assert "sk-or-v1-secretvalue" not in redacted
    assert "yes" not in redacted or "[REDACTED]" in redacted
    assert "hidden chain" not in redacted
    assert "[REDACTED]" in redacted


def test_create_is_exclusive(tmp_path: Path) -> None:
    store = FilesystemRecordStore(tmp_path)
    store.create("run-1")

    with pytest.raises(RunDirectoryExistsError):
        store.create("run-1")


def test_sink_refuses_a_gap_in_sequence(tmp_path: Path) -> None:
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(
        store,
        run_id="run-gap",
        requested_model="scripted",
        seed=0,
        clock=FakeClock(),
    )
    session.start()

    with pytest.raises(ValidationError, match="sequence must be >= 0"):
        RequestSent(
            sequence=-1,
            run_id="run-gap",
            occurred_at=FakeClock().now(),
            requested_message_count=1,
        )
    with pytest.raises(ValueError, match="is not the next expected"):
        session.sink.emit(
            RequestSent(
                sequence=99,
                run_id="run-gap",
                occurred_at=FakeClock().now(),
                requested_message_count=1,
            )
        )


def test_reconstruct_a_fake_matrix_from_files(tmp_path: Path) -> None:
    fixture = development_fixture()
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(
        store,
        run_id="matrix-1",
        requested_model="scripted",
        seed=0,
        clock=FakeClock(),
    )
    session.start()
    client = ScriptedModelClient(_matrix_script(fixture.correct_answer))
    record = run_development_matrix(fixture.prompt, client, 0, session=session)
    session.close()

    rebuilt = reconstruct_run(store.run_dir("matrix-1"))

    assert rebuilt.record.status is RecordStatus.COMPLETE
    assert rebuilt.complete_calls == 13
    assert len(record.branches) == 9
    kinds = [event.kind for event in rebuilt.events]
    assert kinds[0] == "run_started"
    assert kinds[-1] == "run_closed"
    assert kinds.count("request_sent") == 13
    assert kinds.count("response_received") == 13


def test_reconstruct_an_interrupted_run_from_files(tmp_path: Path) -> None:
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(
        store,
        run_id="cut-1",
        requested_model="scripted",
        seed=0,
        clock=FakeClock(),
    )
    session.start()
    session.sink.emit(
        RequestSent(
            sequence=session.sink.next_sequence,
            run_id="cut-1",
            occurred_at=FakeClock().now(),
            requested_message_count=1,
            requested_model="scripted",
            request_hash="abc",
        )
    )

    rebuilt = reconstruct_run(store.run_dir("cut-1"))

    assert rebuilt.interrupted is True
    assert rebuilt.record.status is RecordStatus.INCOMPLETE
    assert rebuilt.events[-1].kind == "request_sent"
    assert not any(event.kind == "run_closed" for event in rebuilt.events)

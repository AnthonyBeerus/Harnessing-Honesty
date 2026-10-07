"""Event and run-record contracts: raw versus derived, and what they refuse."""

from datetime import datetime, timezone
from typing import get_args

import pytest
from pydantic import TypeAdapter, ValidationError

from harnessing_honesty.domain.enums import Failure, RecordStatus, Track
from harnessing_honesty.domain.events import (
    DomainEvent,
    RequestFailed,
    RequestSent,
    ResponseReceived,
    RunClosed,
    RunStarted,
)
from harnessing_honesty.domain.records import RunRecord

STAMP = datetime(2026, 8, 27, tzinfo=timezone.utc)

EXPECTED_KINDS = {
    "RunStarted": "run_started",
    "RunResumed": "run_resumed",
    "RequestSent": "request_sent",
    "ResponseReceived": "response_received",
    "RequestFailed": "request_failed",
    "AttemptInterrupted": "attempt_interrupted",
    "RunClosed": "run_closed",
}


def _union_members() -> tuple[type, ...]:
    annotated_union, _field = get_args(DomainEvent)
    return get_args(annotated_union)


def test_every_event_case_is_in_the_union() -> None:
    names = {member.__name__ for member in _union_members()}

    assert names == set(EXPECTED_KINDS)


def test_the_discriminator_selects_the_case() -> None:
    adapter = TypeAdapter(DomainEvent)

    parsed = adapter.validate_python(
        {
            "kind": "request_failed",
            "sequence": 1,
            "run_id": "run-1",
            "occurred_at": STAMP.isoformat(),
            "failure": "parse",
            "detail": "not json",
        }
    )

    assert isinstance(parsed, RequestFailed)
    assert parsed.failure is Failure.PARSE


def test_an_unknown_event_kind_is_refused() -> None:
    adapter = TypeAdapter(DomainEvent)

    with pytest.raises(ValidationError, match="union_tag_invalid"):
        adapter.validate_python(
            {
                "kind": "score_computed",
                "sequence": 0,
                "run_id": "run-1",
                "occurred_at": STAMP.isoformat(),
            }
        )


def test_events_do_not_carry_the_answer() -> None:
    """Operational evidence, not a second copy of the transcript."""
    for member in _union_members():
        assert "answer" not in member.model_fields
        assert "canonical_answer" not in member.model_fields
        assert "response" not in member.model_fields


def test_every_event_is_sequenced() -> None:
    started = RunStarted(sequence=0, run_id="run-1", occurred_at=STAMP)
    sent = RequestSent(
        sequence=1, run_id="run-1", occurred_at=STAMP, requested_message_count=3
    )
    received = ResponseReceived(
        sequence=2, run_id="run-1", occurred_at=STAMP, observed_message_count=3
    )
    failed = RequestFailed(
        sequence=3,
        run_id="run-1",
        occurred_at=STAMP,
        failure=Failure.PROVIDER,
        detail="429",
    )
    closed = RunClosed(
        sequence=4,
        run_id="run-1",
        occurred_at=STAMP,
        status=RecordStatus.COMPLETE,
    )

    assert [event.sequence for event in (started, sent, received, failed, closed)] == [
        0,
        1,
        2,
        3,
        4,
    ]
    with pytest.raises(ValidationError, match="sequence must be >= 0"):
        RunStarted(sequence=-1, run_id="run-1", occurred_at=STAMP)


def test_a_recorded_event_cannot_be_edited() -> None:
    event = RunStarted(sequence=0, run_id="run-1", occurred_at=STAMP)

    with pytest.raises(ValidationError, match="frozen"):
        event.run_id = "run-2"  # type: ignore[misc]


def test_run_record_requires_model_and_seed() -> None:
    with pytest.raises(ValidationError):
        RunRecord(
            run_id="run-1",
            requested_model="",
            seed=0,
            status=RecordStatus.INCOMPLETE,
        )
    with pytest.raises(ValidationError):
        RunRecord(
            run_id="run-1",
            status=RecordStatus.INCOMPLETE,
        )  # type: ignore[call-arg]


def test_main_execution_without_a_freeze_id_is_refused() -> None:
    with pytest.raises(
        ValidationError,
        match="main execution requires a freeze ID",
    ):
        RunRecord(
            run_id="run-1",
            requested_model="openai/gpt-4o",
            seed=0,
            status=RecordStatus.INCOMPLETE,
            track=Track.MAIN,
        )


def test_a_dev_run_does_not_need_a_freeze_id() -> None:
    record = RunRecord(
        run_id="run-1",
        requested_model="openai/gpt-4o",
        seed=0,
        status=RecordStatus.INCOMPLETE,
    )

    assert record.track is Track.DEV
    assert record.freeze_id is None
    assert record.observed_model is None

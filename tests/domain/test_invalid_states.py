"""Every documented invalid state, with the input that produces it."""

from datetime import datetime, timezone

import pytest
from pydantic import BaseModel, ValidationError

from harnessing_honesty.domain import (
    AnswerKey,
    AnswerResponse,
    AnswerSuccess,
    Condition,
    Failure,
    Message,
    ParseFailure,
    PromptView,
    ProtocolFailure,
    ProviderFailure,
    RecordStatus,
    RequestFailed,
    RequestSent,
    ResponseReceived,
    RunClosed,
    RunRecord,
    RunStarted,
    ScenarioRecord,
)
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily, Track

STAMP = datetime(2026, 8, 27, tzinfo=timezone.utc)
_ANSWER = AnswerResponse(answer="yes")


def _dev_scenario() -> ScenarioRecord:
    return ScenarioRecord(
        prompt=PromptView(id="dev-1", question="Does the conclusion follow?"),
        answer_key=AnswerKey(canonical_answer="yes"),
    )


def test_message_rejects_an_unknown_field_by_name() -> None:
    with pytest.raises(ValidationError, match="hidden") as caught:
        Message(role="user", content="hi", hidden=True)  # type: ignore[call-arg]

    assert "extra_forbidden" in str(caught.value)


_UNKNOWN_FIELD_CASES: tuple[tuple[type[BaseModel], dict[str, object]], ...] = (
    (Message, {"role": "user", "content": "hi"}),
    (PromptView, {"id": "x", "question": "q"}),
    (AnswerKey, {"canonical_answer": "yes"}),
    (
        ScenarioRecord,
        {
            "prompt": PromptView(id="x", question="q"),
            "answer_key": AnswerKey(canonical_answer="yes"),
        },
    ),
    (
        Condition,
        {"pressure": PressureFamily.CONTRADICTION, "policy": PolicyFamily.NONE},
    ),
    (AnswerResponse, {"answer": "yes", "confidence": 1.0, "rationale": "r"}),
    (AnswerSuccess, {"response": _ANSWER, "requested_message_count": 1}),
    (ParseFailure, {"detail": "bad"}),
    (ProviderFailure, {"detail": "down"}),
    (ProtocolFailure, {"detail": "cache HIT"}),
    (RunStarted, {"sequence": 0, "run_id": "run-1", "occurred_at": STAMP}),
    (
        RequestSent,
        {
            "sequence": 1,
            "run_id": "run-1",
            "occurred_at": STAMP,
            "requested_message_count": 1,
        },
    ),
    (ResponseReceived, {"sequence": 2, "run_id": "run-1", "occurred_at": STAMP}),
    (
        RequestFailed,
        {
            "sequence": 3,
            "run_id": "run-1",
            "occurred_at": STAMP,
            "failure": Failure.PROVIDER,
            "detail": "down",
        },
    ),
    (
        RunClosed,
        {
            "sequence": 4,
            "run_id": "run-1",
            "occurred_at": STAMP,
            "status": RecordStatus.COMPLETE,
        },
    ),
    (
        RunRecord,
        {
            "run_id": "run-1",
            "requested_model": "openai/gpt-4o",
            "seed": 0,
            "status": RecordStatus.INCOMPLETE,
        },
    ),
)


@pytest.mark.parametrize(
    ("model", "payload"),
    _UNKNOWN_FIELD_CASES,
    ids=[model.__name__ for model, _ in _UNKNOWN_FIELD_CASES],
)
def test_every_domain_type_rejects_unknown_fields(
    model: type[BaseModel], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError, match="hidden"):
        model.model_validate({**payload, "hidden": True})


def test_run_record_without_a_requested_model_is_refused() -> None:
    with pytest.raises(ValidationError, match="requested_model"):
        RunRecord(
            run_id="run-1",
            seed=0,
            status=RecordStatus.INCOMPLETE,
        )  # type: ignore[call-arg]


def test_run_record_without_a_seed_is_refused() -> None:
    with pytest.raises(ValidationError, match="seed"):
        RunRecord(
            run_id="run-1",
            requested_model="openai/gpt-4o",
            status=RecordStatus.INCOMPLETE,
        )  # type: ignore[call-arg]


def test_run_record_rejects_an_empty_requested_model() -> None:
    with pytest.raises(ValidationError, match="must be nonempty"):
        RunRecord(
            run_id="run-1",
            requested_model="  ",
            seed=0,
            status=RecordStatus.INCOMPLETE,
        )



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

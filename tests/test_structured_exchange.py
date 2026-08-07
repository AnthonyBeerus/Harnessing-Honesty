import inspect

import pytest
from pydantic_core import ValidationError

from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ParseFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.protocol import ModelClient
from harnessing_honesty.scenarios import (
    DEVELOPMENT_LOGIC_ANSWER,
    DEVELOPMENT_LOGIC_QUESTION,
    DEVELOPMENT_LOGIC_RATIONALE,
)


def test_fake_preserves_exact_role_order() -> None:
    messages = (
        Message(role="system", content="Be concise."),
        Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),
    )
    client = ScriptedModelClient(
        [
            AnswerSuccess(
                response=AnswerResponse(
                    answer=DEVELOPMENT_LOGIC_ANSWER,
                    confidence=0.9,
                    rationale=DEVELOPMENT_LOGIC_RATIONALE,
                ),
                message_count=2,
            )
        ]
    )

    client.complete(messages)

    assert client.requests == [messages]


def test_message_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Message(role="user", content="hi", hidden=True)  # type: ignore[call-arg]


def test_confidence_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        AnswerResponse(
            answer=DEVELOPMENT_LOGIC_ANSWER,
            confidence=1.5,
            rationale="nope",
        )


def test_malformed_scripted_output_is_parse_failure() -> None:
    client = ScriptedModelClient(
        [ParseFailure(detail="not valid AnswerResponse JSON")]
    )

    result = client.complete(
        (Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),)
    )

    assert result == ParseFailure(detail="not valid AnswerResponse JSON")


def test_complete_requires_message_tuple_not_plain_string() -> None:
    signature = inspect.signature(ModelClient.complete)
    parameter = signature.parameters["messages"]
    assert parameter.annotation == tuple[Message, ...]
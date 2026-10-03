"""Response states and the one yes/no normalization.

Only surrounding whitespace and letter case may change a raw response into a
valid answer. Everything else stays invalid with its raw text retained.
"""

import typing

import pytest
from pydantic import TypeAdapter
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
    ResponseState,
    normalize_binary_answer,
    response_state,
)
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("yes", "yes"),
        ("no", "no"),
        ("YES", "yes"),
        ("No", "no"),
        (" yEs ", "yes"),
        ("\n\tno\r\n", "no"),
        ("yes.", None),
        ("no!", None),
        ("'yes'", None),
        ('"no"', None),
        ("**yes**", None),
        ("`no`", None),
        ("yes, because", None),
        ("Answer: yes", None),
        ("y", None),
        ("nope", None),
        ("yes no", None),
        ("y e s", None),
        ("true", None),
        ("", None),
        ("   ", None),
        ("ｙｅｓ", None),
    ],
)
def test_only_whitespace_and_case_are_normalized(
    raw: str, expected: str | None
) -> None:
    assert normalize_binary_answer(raw) == expected


_SUCCESS = AnswerSuccess(
    response=AnswerResponse(answer="no"),
    raw_response=" No ",
    requested_message_count=1,
)

EXPECTED_STATE: dict[str, tuple[ModelResult, ResponseState]] = {
    "AnswerSuccess": (_SUCCESS, ResponseState.VALID),
    "ParseFailure": (
        ParseFailure(detail="bad", raw_response="no."),
        ResponseState.INVALID,
    ),
    "ProviderFailure": (
        ProviderFailure(detail="timeout"),
        ResponseState.PROVIDER_FAILURE,
    ),
    "ProtocolFailure": (
        ProtocolFailure(detail="route"),
        ResponseState.PROTOCOL_FAILURE,
    ),
}


def test_every_result_case_has_a_declared_state() -> None:
    annotated_union, _field = typing.get_args(ModelResult)
    members = {member.__name__ for member in typing.get_args(annotated_union)}

    assert members == set(EXPECTED_STATE)


@pytest.mark.parametrize("name", sorted(EXPECTED_STATE))
def test_response_state_follows_the_result_case(name: str) -> None:
    result, state = EXPECTED_STATE[name]

    assert response_state(result) is state


def test_an_unfilled_slot_is_missing_not_a_failure() -> None:
    assert response_state(None) is ResponseState.MISSING


def test_states_cover_the_enum_exactly() -> None:
    produced = {state for _result, state in EXPECTED_STATE.values()}

    assert produced | {ResponseState.MISSING} == set(ResponseState)


def test_a_parse_failure_event_without_raw_text_still_loads() -> None:
    stored = {"kind": "parse_failure", "detail": "not json"}

    result = TypeAdapter(ModelResult).validate_python(stored)

    assert result == ParseFailure(detail="not json")
    assert result.raw_response is None


def test_the_client_keeps_the_raw_text_of_an_invalid_answer() -> None:
    agent = Agent[None, str](TestModel(custom_output_text="Yes."))
    client = PydanticAIModelClient(agent)

    result = client.complete((Message(role="user", content="Is it?"),))

    assert isinstance(result, ParseFailure)
    assert result.raw_response == "Yes."
    assert response_state(result) is ResponseState.INVALID

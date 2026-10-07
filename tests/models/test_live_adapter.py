from datetime import datetime, timezone
import json

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from harnessing_honesty.models.config import DecodingCard, RoutingCard, ServingManifest
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ProtocolFailure,
)
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient
from harnessing_honesty.evaluation.fixtures.scenarios import DEVELOPMENT_LOGIC_QUESTION


def test_live_adapter_parses_plain_text_into_an_answer_record() -> None:
    agent = Agent[None, str](TestModel(custom_output_text=" YeS "))
    client = PydanticAIModelClient(agent)

    result = client.complete(
        (Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),)
    )

    assert isinstance(result, AnswerSuccess)
    assert isinstance(result.response, AnswerResponse)
    assert result.response.answer == "yes"
    assert result.raw_response == " YeS "



def _pinned_manifest() -> ServingManifest:
    return ServingManifest(
        requested_model="google/gemma-3-27b-it",
        routing=RoutingCard(
            provider_only=("deepinfra",),
            provider_order=("deepinfra",),
        ),
        decoding=DecodingCard(reasoning="off", reasoning_control="unresolved"),
    )


def test_extracts_downstream_provider_from_response() -> None:
    class _Response:
        provider_details = {
            "downstream_provider": "DeepInfra",
            "finish_reason": "tool_calls",
            "timestamp": datetime(2026, 9, 1, 23, 16, 12, tzinfo=timezone.utc),
        }
        model_name = "google/gemma-3-27b-it"

    class _Result:
        provider_details = None
        response = _Response()

    client = PydanticAIModelClient(Agent(TestModel(custom_output_text="yes")))
    envelope = client._extract_envelope(_Result())

    assert envelope is not None
    assert envelope["provider"] == "deepinfra"
    assert envelope["model"] == "google/gemma-3-27b-it"
    json.dumps(envelope)


def test_missing_envelope_with_manifest_is_protocol_failure() -> None:
    client = PydanticAIModelClient(
        Agent(TestModel(custom_output_text="yes")),
        manifest=_pinned_manifest(),
    )

    result = client.complete((Message(role="user", content="Is 2 even?"),))

    assert isinstance(result, ProtocolFailure)
    assert "no provider identity" in result.detail

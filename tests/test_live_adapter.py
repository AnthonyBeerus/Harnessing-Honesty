import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.models.pydantic_ai_client import (
    DevelopmentModelConfigurationError,
    PydanticAIModelClient,
)
from harnessing_honesty.scenarios import DEVELOPMENT_LOGIC_QUESTION


def test_live_adapter_uses_structured_answer_response() -> None:
    agent = Agent[None, AnswerResponse](TestModel(), output_type=AnswerResponse)
    client = PydanticAIModelClient(agent)

    result = client.complete(
        (Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),)
    )

    assert isinstance(result, AnswerSuccess)
    assert isinstance(result.response, AnswerResponse)
    assert 0.0 <= result.response.confidence <= 1.0


def test_environment_factory_fails_before_a_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "harnessing_honesty.models.pydantic_ai_client.load_dotenv",
        lambda: None,
    )
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HARNESS_DEV_MODEL", raising=False)

    with pytest.raises(
        DevelopmentModelConfigurationError,
        match="OPENROUTER_API_KEY, HARNESS_DEV_MODEL",
    ):
        PydanticAIModelClient.from_environment()
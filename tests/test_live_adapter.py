import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from harnessing_honesty.models.pydantic_ai_client import (
    DevelopmentModelConfigurationError,
    PydanticAIModelClient,
)


def test_live_adapter_uses_the_common_response_boundary() -> None:
    client = PydanticAIModelClient(Agent(TestModel()))

    response = client.complete("What is 2 + 2?")

    assert response.text == "success (no tool calls)"


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
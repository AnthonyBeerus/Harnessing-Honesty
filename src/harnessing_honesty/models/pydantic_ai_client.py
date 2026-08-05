import os

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from harnessing_honesty.models.protocol import ModelResponse

class DevelopmentModelConfigurationError(RuntimeError):
    """Raised when required development model environment variables are missing."""

class PydanticAIModelClient:
    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    @classmethod
    def from_environment(cls) -> "PydanticAIModelClient":
        """Build a client from environment variables via OpenRouter.

        Requires ``OPENROUTER_API_KEY`` and ``HARNESS_DEV_MODEL`` to be set,
        typically in a ``.env`` file loaded by ``python-dotenv``.
        """
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        model_name = os.getenv("HARNESS_DEV_MODEL")

        missing = [
            name
            for name, value in (
                ("OPENROUTER_API_KEY", api_key),
                ("HARNESS_DEV_MODEL", model_name),
            )
            if not value
        ] 
        if missing:
            names = ", ".join(missing)
            raise DevelopmentModelConfigurationError(
                f"Missing development model configuration: {names}"
            )
        assert api_key is not None
        assert model_name is not None
        provider = OpenAIProvider(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        model = OpenAIChatModel(model_name, provider=provider)
        agent = Agent(model)
        return cls(agent)

    def complete(self, prompt: str) -> ModelResponse:
        result = self._agent.run_sync(prompt)
        return ModelResponse(text=result.output)
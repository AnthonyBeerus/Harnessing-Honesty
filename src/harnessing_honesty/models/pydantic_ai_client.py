import os

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from harnessing_honesty.models.protocol import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ModelResult,
    ParseFailure,
    ProviderFailure,
)


class DevelopmentModelConfigurationError(RuntimeError):
    """Raised when required development model environment variables are missing."""


class PydanticAIModelClient:
    def __init__(self, agent: Agent[None, AnswerResponse]) -> None:
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

        provider = OpenRouterProvider(api_key=api_key)
        model = OpenRouterModel(model_name, provider=provider)
        agent = Agent(model, output_type=AnswerResponse)
        return cls(agent)

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        try:
            user_prompt, instructions = _split_prompt(messages)
            result = self._agent.run_sync(
                user_prompt,
                instructions=instructions,
            )
        except UnexpectedModelBehavior as exc:
            detail = str(exc)
            # OpenRouter sometimes returns null completion shells; that is a
            # provider transport failure, not an AnswerResponse schema miss.
            if "chat completions endpoint" in detail.lower():
                return ProviderFailure(detail=detail)
            return ParseFailure(detail=detail)
        except ModelHTTPError as exc:
            return ProviderFailure(detail=str(exc))
        except Exception as exc:  # provider / transport / unexpected
            return ProviderFailure(detail=str(exc))

        return AnswerSuccess(
            response=result.output,
            message_count=len(messages),
        )


def _split_prompt(messages: tuple[Message, ...]) -> tuple[str, str | None]:
    """Split harness messages into Pydantic AI user prompt and instructions."""
    system_parts = [message.content for message in messages if message.role == "system"]
    user_parts = [message.content for message in messages if message.role == "user"]
    if not user_parts:
        raise ValueError("No user messages found in the conversation.")

    instructions = "\n\n".join(system_parts) if system_parts else None
    user_prompt = user_parts[-1]
    return user_prompt, instructions

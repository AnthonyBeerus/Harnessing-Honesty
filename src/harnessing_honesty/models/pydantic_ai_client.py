import os

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelRequestPart,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.responses import AnswerResponse
from harnessing_honesty.domain.results import (
    AnswerSuccess,
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
            user_prompt, instructions, history = _to_provider_request(messages)
            result = self._agent.run_sync(
                user_prompt,
                instructions=instructions,
                message_history=history,
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
            requested_message_count=len(messages),
            observed_message_count=_observed_message_count(
                messages, result.all_messages()
            ),
        )


class UnmappableRequestError(ValueError):
    """Raised when a harness request cannot be projected onto the provider."""


def _observed_message_count(
    messages: tuple[Message, ...],
    assembled: list[ModelMessage],
) -> int:
    """Count harness turns that demonstrably reached the provider.

    Read back from the conversation the agent assembled, not from the
    projection that built it. A count derived from the projection's own
    bookkeeping would agree with the projection by construction and could
    not witness the projection dropping a turn.

    Conversation turns are counted up to the model's own reply; system turns
    are counted where their content appears in the delivered instructions.
    """
    delivered = 0
    for message in assembled:
        if isinstance(message, ModelResponse):
            if not all(isinstance(part, TextPart) for part in message.parts):
                break  # the model's own reply; everything after is internal
            delivered += len(message.parts)
        else:
            delivered += sum(
                isinstance(part, UserPromptPart) for part in message.parts
            )

    instructions = next(
        (
            message.instructions
            for message in assembled
            if isinstance(message, ModelRequest) and message.instructions
        ),
        "",
    )
    delivered += sum(
        1
        for message in messages
        if message.role == "system" and message.content in instructions
    )
    return delivered


# Harness roles that become user-role turns on the wire. ``tool`` is here
# because the harness verifier output is fixed text, not a live tool call:
# there is no preceding tool call for a provider tool result to answer, and
# synthesising one would add an assistant turn to the tool cells only, which
# is exactly what the registered call-matching rule forbids.
_USER_SIDE_ROLES = frozenset({"user", "tool"})


def _to_provider_request(
    messages: tuple[Message, ...],
) -> tuple[str, str | None, list[ModelMessage]]:
    """Project harness messages onto a Pydantic AI request.

    Returns the final user prompt, the joined instructions, and every
    preceding turn as history. ``system`` turns become instructions;
    ``assistant`` turns become model responses; ``user`` and ``tool`` turns
    become user-role turns.

    The whole conversation crosses the wire. A pressured turn is only a
    pressured turn if the model can still see the question it is being
    pressured about.
    """
    instructions = "\n\n".join(
        message.content for message in messages if message.role == "system"
    )
    conversation = [message for message in messages if message.role != "system"]
    if not conversation:
        raise UnmappableRequestError("No conversation turns to send.")

    final = conversation[-1]
    if final.role not in _USER_SIDE_ROLES:
        raise UnmappableRequestError(
            f"The last turn must be user-side, not {final.role!r}. "
            "The provider is being asked to answer, so something must be asked."
        )

    history: list[ModelMessage] = []
    pending: list[ModelRequestPart] = []
    for message in conversation[:-1]:
        if message.role == "assistant":
            if pending:
                history.append(ModelRequest(parts=pending))
                pending = []
            history.append(ModelResponse(parts=[TextPart(content=message.content)]))
        else:
            pending.append(UserPromptPart(content=message.content))
    if pending:
        history.append(ModelRequest(parts=pending))

    return final.content, instructions or None, history

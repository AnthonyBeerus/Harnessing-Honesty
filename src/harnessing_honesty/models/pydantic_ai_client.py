import os
from typing import cast

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
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
from pydantic_ai.models.openrouter import (
    OpenRouterModel,
    OpenRouterModelSettings,
    OpenRouterProviderName,
)
from pydantic_ai.providers.openrouter import OpenRouterProvider

from harnessing_honesty.models.config import ServingManifest
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.responses import (
    AnswerResponse,
    normalize_binary_answer,
)
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
)
from harnessing_honesty.domain.evidence import CallEvidence
from harnessing_honesty.models.routing import classify_envelope
from harnessing_honesty.models.transport import CapturingTransport, call_evidence


class DevelopmentModelConfigurationError(RuntimeError):
    """Raised when the serving manifest or API key is missing."""


class PydanticAIModelClient:
    def __init__(
        self,
        agent: Agent[None, str],
        manifest: ServingManifest | None = None,
        capture: CapturingTransport | None = None,
    ) -> None:
        self._agent = agent
        self._manifest = manifest
        self._capture = capture
        self.last_envelope: dict[str, object] | None = None
        self.last_evidence: CallEvidence | None = None
        self.envelopes: list[dict[str, object]] = []

    @classmethod
    def from_environment(cls) -> "PydanticAIModelClient":
        """Closed. A key plus a slug is not a served-system identity."""
        raise DevelopmentModelConfigurationError(
            "from_environment is closed: use from_manifest with a routing card"
        )

    @classmethod
    def from_manifest(
        cls,
        manifest: ServingManifest,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> "PydanticAIModelClient":
        """Build a fail-closed OpenRouter client from a serving card.

        ``transport`` replaces the network in offline tests.
        """
        # Provider selection and fallback controls follow OpenRouter's documented
        # request fields [32]. The installed SDK boundary is Pydantic AI 1.107.1 [43].
        settings: OpenRouterModelSettings = {
            "temperature": manifest.decoding.temperature,
            "openrouter_provider": {
                "only": _provider_slugs(manifest.routing.provider_only),
                "order": _provider_slugs(manifest.routing.provider_order),
                "allow_fallbacks": False,
                "require_parameters": True,
            },
            "openrouter_usage": {"include": True},
        }
        if manifest.decoding.seed is not None:
            settings["seed"] = manifest.decoding.seed
        if manifest.decoding.max_tokens is not None:
            # OpenAI SDK emits max_completion_tokens; OpenRouter's
            # require_parameters check uses the pin's list, which names
            # max_tokens (Anthropic, GPT-4o). extra_body keeps the cap.
            settings["extra_body"] = {"max_tokens": manifest.decoding.max_tokens}
        # Plain text avoids adding a response-format tool to every policy arm.
        # Pydantic AI 1.107.1 uses text output when ``str`` is requested [43].
        capture = CapturingTransport(transport or httpx.AsyncHTTPTransport())
        agent = openrouter_text_agent(
            manifest.requested_model, settings, api_key, capture=capture
        )
        return cls(agent, manifest=manifest, capture=capture)

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        """Run one logical call. ``last_evidence`` covers this call only."""
        self.last_envelope = None
        self.last_evidence = None
        start = len(self._capture.exchanges) if self._capture else 0
        try:
            return self._complete(messages)
        finally:
            if self._capture is not None:
                self.last_evidence = call_evidence(self._capture.exchanges[start:])

    def _complete(self, messages: tuple[Message, ...]) -> ModelResult:
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
            # provider transport failure, not a binary-answer parse miss.
            if "chat completions endpoint" in detail.lower():
                return ProviderFailure(detail=detail)
            return ParseFailure(detail=detail)
        except ModelHTTPError as exc:
            return ProviderFailure(detail=str(exc))
        except Exception as exc:  # provider / transport / unexpected
            return ProviderFailure(detail=str(exc))

        # OpenRouter generation metadata supplies observed provider evidence [34].
        envelope = self._extract_envelope(result)
        if envelope is None:
            if self._manifest is not None:
                return ProtocolFailure(detail="envelope has no provider identity")
        else:
            self.last_envelope = envelope
            self.envelopes.append(envelope)
            failure = self.inspect_envelope(envelope)
            if failure is not None:
                return failure

        if not isinstance(result.output, str):
            return ParseFailure(detail="model output was not text")
        raw_response = result.output
        normalized = normalize_binary_answer(raw_response)
        if normalized is None:
            return ParseFailure(
                detail=f"expected exactly yes or no; received {raw_response!r}",
                raw_response=raw_response,
            )

        return AnswerSuccess(
            response=AnswerResponse(answer=normalized),
            raw_response=raw_response,
            requested_message_count=len(messages),
            observed_message_count=_observed_message_count(
                messages, result.all_messages()
            ),
        )

    def inspect_envelope(self, envelope: dict[str, object]) -> ProtocolFailure | None:
        """Classify a captured envelope. Called before the parse is accepted."""
        self.last_envelope = envelope
        if envelope.get("finish_reason") == "tool_calls":
            return ProtocolFailure(
                detail="plain-text response unexpectedly finished with tool_calls"
            )
        if self._manifest is None:
            return None
        return classify_envelope(envelope, self._manifest)

    def _extract_envelope(self, result: object) -> dict[str, object] | None:
        raw = getattr(result, "provider_details", None) or getattr(
            result, "provider_response", None
        )
        response = getattr(result, "response", None)
        if not isinstance(raw, dict) and response is not None:
            raw = getattr(response, "provider_details", None)
        if not isinstance(raw, dict):
            return None
        safe = _json_safe(raw)
        if not isinstance(safe, dict):
            return None
        envelope: dict[str, object] = safe
        if "provider" not in envelope:
            downstream = envelope.get("downstream_provider")
            if isinstance(downstream, str) and downstream.strip():
                envelope["provider"] = downstream.strip().lower()
        if "model" not in envelope and response is not None:
            model_name = getattr(response, "model_name", None)
            if isinstance(model_name, str) and model_name:
                envelope["model"] = model_name
        if not envelope.get("provider") and not envelope.get("downstream_provider"):
            return None
        return envelope


def _provider_slugs(names: tuple[str, ...]) -> list[OpenRouterProviderName]:
    return [cast(OpenRouterProviderName, name) for name in names]


def openrouter_text_agent(
    model_name: str,
    settings: OpenRouterModelSettings,
    api_key: str | None = None,
    capture: CapturingTransport | None = None,
) -> Agent[None, str]:
    """Build the plain-text OpenRouter agent.

    With ``capture``, SDK retries are off and every attempt is recorded.
    Construction scripts omit it and keep SDK defaults.
    """
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise DevelopmentModelConfigurationError(
            "Missing development model configuration: OPENROUTER_API_KEY"
        )
    provider = OpenRouterProvider(api_key=key)
    if capture is not None:
        # openai-python 2.53.0 retries twice by default [93]. Pydantic AI
        # 1.107.1 accepts a prebuilt AsyncOpenAI client [43].
        client = AsyncOpenAI(
            base_url=provider.base_url,
            api_key=key,
            max_retries=0,
            http_client=httpx.AsyncClient(transport=capture),
        )
        provider = OpenRouterProvider(openai_client=client)
    model = OpenRouterModel(model_name, provider=provider)
    return Agent(model, output_type=str, model_settings=settings)


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return value


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
    response_indexes = [
        index
        for index, message in enumerate(assembled)
        if isinstance(message, ModelResponse)
    ]
    final_response = response_indexes[-1] if response_indexes else len(assembled)
    delivered = 0
    for index, message in enumerate(assembled):
        if index == final_response:
            break
        if isinstance(message, ModelResponse):
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


def _to_provider_request(
    messages: tuple[Message, ...],
) -> tuple[str, str | None, list[ModelMessage]]:
    """Project harness messages onto a Pydantic AI request.

    Returns the final user prompt, the joined instructions, and every
    preceding turn as history. ``system`` turns become instructions;
    ``assistant`` turns become model responses and ``user`` turns remain user
    turns. External verification is explicitly labelled in its user-side text.

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
    if final.role != "user":
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

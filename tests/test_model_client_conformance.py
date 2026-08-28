"""One ModelClient suite, held against two implementations.

The scripted client cannot fail a transport assertion: it echoes the tuple
it was handed. A FunctionModel-backed live client can, because it records
what the provider actually received. Leaving that client out of the
parameter list would rebuild the false comfort of ``test_live_adapter``.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ParseFailure,
    ProviderFailure,
)
from harnessing_honesty.domain.protocols import ModelClient
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient

CONVERSATION = (
    Message(role="user", content="QUESTION-TEXT"),
    Message(role="assistant", content="PRIOR-ANSWER-JSON"),
    Message(role="user", content="PRESSURE-TEXT"),
    Message(role="tool", content="VERIFIER-OUTPUT"),
    Message(role="user", content="POLICY-TEXT"),
)

_SUCCESS = AnswerSuccess(
    response=AnswerResponse(answer="yes", confidence=1.0, rationale="ok"),
    requested_message_count=len(CONVERSATION),
)
_USER_SIDE = frozenset({"user", "tool"})
Wire = list[tuple[str, str]]
Observer = Callable[[], Wire]


def _flatten(messages: list[ModelMessage]) -> Wire:
    pairs: Wire = []
    for message in messages:
        if isinstance(message, ModelRequest):
            pairs.extend(
                ("user", str(part.content))
                for part in message.parts
                if isinstance(part, UserPromptPart)
            )
        elif isinstance(message, ModelResponse):
            pairs.extend(
                ("assistant", part.content)
                for part in message.parts
                if isinstance(part, TextPart)
            )
    return pairs


class _FunctionBody:
    """Record the provider request, then produce or raise a response."""

    __name__ = "conformance_provider"

    def __init__(self, respond: Callable[..., ModelResponse]) -> None:
        self._respond = respond
        self.captured: list[list[ModelMessage]] = []

    def __call__(
        self, messages: list[ModelMessage], info: AgentInfo
    ) -> ModelResponse:
        self.captured.append(messages)
        return self._respond(messages, info)


def _valid_answer(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    assert info.output_tools
    return ModelResponse(
        parts=[
            ToolCallPart(
                info.output_tools[0].name,
                {"answer": "yes", "confidence": 1.0, "rationale": "ok"},
            )
        ]
    )


def _invalid_answer(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    assert info.output_tools
    return ModelResponse(
        parts=[ToolCallPart(info.output_tools[0].name, {"answer": "yes"})]
    )


def _http_error(_messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
    raise ModelHTTPError(
        status_code=429, model_name="conformance", body="rate limited"
    )


def _live_pair(
    respond: Callable[..., ModelResponse],
) -> tuple[PydanticAIModelClient, _FunctionBody]:
    body = _FunctionBody(respond)
    agent = Agent[None, AnswerResponse](
        FunctionModel(body), output_type=AnswerResponse
    )
    return PydanticAIModelClient(agent), body


def _identity_project(messages: tuple[Message, ...]) -> Wire:
    return [(str(message.role), message.content) for message in messages]


def _wire_project(messages: tuple[Message, ...]) -> Wire:
    """The live client's documented projection: tool becomes user-role."""
    pairs: Wire = []
    for message in messages:
        role = str(message.role)
        if role == "system":
            continue
        projected = "user" if role in _USER_SIDE else role
        pairs.append((projected, message.content))
    return pairs


@dataclass(frozen=True)
class _Backend:
    success: Callable[[], tuple[ModelClient, Observer]]
    malformed: Callable[[], ModelClient]
    unavailable: Callable[[], ModelClient]
    project: Callable[[tuple[Message, ...]], Wire]


def _scripted_success() -> tuple[ModelClient, Observer]:
    client = ScriptedModelClient([_SUCCESS])
    return client, lambda: _identity_project(client.requests[-1])


def _live_success() -> tuple[ModelClient, Observer]:
    client, body = _live_pair(_valid_answer)
    return client, lambda: _flatten(body.captured[-1])


SCRIPTED = _Backend(
    success=_scripted_success,
    malformed=lambda: ScriptedModelClient(
        [ParseFailure(detail="not valid AnswerResponse JSON")]
    ),
    unavailable=lambda: ScriptedModelClient(
        [ProviderFailure(detail="status_code: 429")]
    ),
    project=_identity_project,
)

LIVE = _Backend(
    success=_live_success,
    malformed=lambda: _live_pair(_invalid_answer)[0],
    unavailable=lambda: _live_pair(_http_error)[0],
    project=_wire_project,
)


@pytest.mark.parametrize("backend", [SCRIPTED, LIVE], ids=["scripted", "live"])
def test_complete_returns_a_result_and_preserves_the_wire(backend: _Backend) -> None:
    client, observed = backend.success()

    result = client.complete(CONVERSATION)

    assert isinstance(result, AnswerSuccess)
    assert observed() == backend.project(CONVERSATION)


@pytest.mark.parametrize("backend", [SCRIPTED, LIVE], ids=["scripted", "live"])
def test_malformed_output_is_a_parse_failure_not_an_exception(
    backend: _Backend,
) -> None:
    result = backend.malformed().complete(CONVERSATION)

    assert isinstance(result, ParseFailure)


@pytest.mark.parametrize("backend", [SCRIPTED, LIVE], ids=["scripted", "live"])
def test_a_provider_error_is_a_provider_failure_not_an_exception(
    backend: _Backend,
) -> None:
    result = backend.unavailable().complete(CONVERSATION)

    assert isinstance(result, ProviderFailure)

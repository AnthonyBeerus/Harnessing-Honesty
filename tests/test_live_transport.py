"""Transport fidelity: the provider must receive what the harness built.

``test_live_adapter`` checks protocol conformance -- that ``complete`` matches
the signature and returns a ``ModelResult``. That is a different property. A
client can satisfy the signature perfectly while discarding most of the
request, and a single-message test cannot tell the difference because dropping
history is a no-op when there is no history.

These tests capture what actually reaches the provider and compare it, role by
role, against the tuple the harness handed over.
"""

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from harnessing_honesty.models import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient

TOOL_CELL_REQUEST = (
    Message(role="user", content="QUESTION-TEXT"),
    Message(role="assistant", content="PRIOR-ANSWER-JSON"),
    Message(role="user", content="PRESSURE-TEXT"),
    Message(role="tool", content="VERIFIER-OUTPUT"),
    Message(role="user", content="POLICY-TEXT"),
)


def _flatten(messages: list[ModelMessage]) -> list[tuple[str, str]]:
    """Project captured provider messages back into (role, content) pairs."""
    pairs: list[tuple[str, str]] = []
    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, SystemPromptPart):
                    pairs.append(("system", part.content))
                elif isinstance(part, UserPromptPart):
                    pairs.append(("user", str(part.content)))
                elif isinstance(part, ToolReturnPart):
                    pairs.append(("tool", str(part.content)))
        elif isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, TextPart):
                    pairs.append(("assistant", part.content))
                elif isinstance(part, ToolCallPart):
                    pairs.append(("assistant-tool-call", part.tool_name))
    return pairs


class CapturingProvider:
    """A ``FunctionModel`` body that records every request it is handed."""

    # FunctionModel names itself from the callable it wraps.
    __name__ = "capturing_provider"

    def __init__(self) -> None:
        self.captured: list[list[ModelMessage]] = []

    def __call__(
        self, messages: list[ModelMessage], info: AgentInfo
    ) -> ModelResponse:
        self.captured.append(messages)
        assert info.output_tools, "expected a structured output tool"
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "answer": "yes",
                        "confidence": 1.0,
                        "rationale": "captured",
                    },
                )
            ]
        )

    @property
    def last(self) -> list[tuple[str, str]]:
        return _flatten(self.captured[-1])


def _capturing_client() -> tuple[PydanticAIModelClient, CapturingProvider]:
    provider = CapturingProvider()
    agent = Agent[None, AnswerResponse](
        FunctionModel(provider), output_type=AnswerResponse
    )
    return PydanticAIModelClient(agent), provider


def test_every_message_reaches_the_provider() -> None:
    """A five-message tool cell must arrive as five messages, not one."""
    client, provider = _capturing_client()

    client.complete(TOOL_CELL_REQUEST)

    delivered = provider.last
    assert len(delivered) == len(TOOL_CELL_REQUEST), (
        f"harness built {len(TOOL_CELL_REQUEST)} messages, "
        f"provider received {len(delivered)}: {delivered}"
    )


def test_roles_and_order_survive_the_transport() -> None:
    """Order is preserved and roles follow one documented projection.

    ``tool`` becomes a user-role turn. The harness verifier output is fixed
    text, not a live tool call, so there is no preceding tool call for a
    provider tool result to answer. This is a registered projection, not a
    silent one.
    """
    client, provider = _capturing_client()

    client.complete(TOOL_CELL_REQUEST)

    assert provider.last == [
        ("user", "QUESTION-TEXT"),
        ("assistant", "PRIOR-ANSWER-JSON"),
        ("user", "PRESSURE-TEXT"),
        ("user", "VERIFIER-OUTPUT"),
        ("user", "POLICY-TEXT"),
    ]


def test_the_tool_cell_gains_no_extra_assistant_turn() -> None:
    """The call-matching rule holds on the wire, not just in the harness.

    Synthesising a tool call to carry the verifier output would give the tool
    cells an assistant turn the comparison policies do not have, making the
    contrast one of revision opportunities rather than shown content.
    """
    client, provider = _capturing_client()

    client.complete(TOOL_CELL_REQUEST)
    with_tool = [role for role, _ in provider.last].count("assistant")

    client.complete(
        tuple(
            message
            for message in TOOL_CELL_REQUEST
            if message.role != "tool"
        )
    )
    without_tool = [role for role, _ in provider.last].count("assistant")

    assert with_tool == without_tool == 1


def test_the_question_reaches_the_pressured_turn() -> None:
    """The construct depends on this.

    A regressive shift is a correct answer abandoned under pressure. If the
    scenario question never reaches the pressured call, there is no answer to
    abandon and the primary outcome measures nothing.
    """
    client, provider = _capturing_client()

    client.complete(TOOL_CELL_REQUEST)

    contents = [content for _, content in provider.last]
    assert "QUESTION-TEXT" in contents
    assert "PRIOR-ANSWER-JSON" in contents
    assert "PRESSURE-TEXT" in contents


def test_counts_agree_when_the_transport_is_lossless() -> None:
    client, _ = _capturing_client()

    result = client.complete(TOOL_CELL_REQUEST)

    assert isinstance(result, AnswerSuccess)
    assert result.requested_message_count == len(TOOL_CELL_REQUEST)
    assert result.observed_message_count == len(TOOL_CELL_REQUEST)


def test_system_turns_are_counted_through_the_instruction_channel() -> None:
    """Instructions are a separate channel but still delivered content."""
    client, _ = _capturing_client()

    result = client.complete(
        (
            Message(role="system", content="SYSTEM-TEXT"),
            Message(role="user", content="QUESTION-TEXT"),
        )
    )

    assert isinstance(result, AnswerSuccess)
    assert result.requested_message_count == 2
    assert result.observed_message_count == 2


def test_a_lossy_projection_makes_the_counts_disagree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression guard, using the exact shape of the shipped defect.

    Restoring the old behaviour -- keep the last user turn, discard the rest
    -- must now be visible in the record rather than answered confidently
    and stored as if five turns had been sent.
    """

    def lossy(messages: tuple[Message, ...]):
        return messages[-1].content, None, []

    monkeypatch.setattr(
        "harnessing_honesty.models.pydantic_ai_client._to_provider_request",
        lossy,
    )
    client, provider = _capturing_client()

    result = client.complete(TOOL_CELL_REQUEST)

    assert isinstance(result, AnswerSuccess)
    assert result.requested_message_count == 5
    assert result.observed_message_count == 1
    assert provider.last == [("user", "POLICY-TEXT")]


def test_system_messages_still_become_instructions() -> None:
    """System turns are instructions, not conversation, and stay that way."""
    client, provider = _capturing_client()

    client.complete(
        (
            Message(role="system", content="SYSTEM-TEXT"),
            Message(role="user", content="QUESTION-TEXT"),
        )
    )

    delivered = provider.last
    assert ("user", "QUESTION-TEXT") in delivered
    assert all(role != "system" for role, _ in delivered)

from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Message(BaseModel):
    """A message in a conversation.
    Frozen so request snapshots cannot be edited after a call.
    Extra fields are forbidden so harness metadata cannot be smuggled in.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user", "assistant", "tool"]
    content: str


class AnswerResponse(BaseModel):
    """A response from the model.

    Confidence bounds are enforced in Python only. ``Field(ge=..., le=...)``
    emits JSON Schema minimum/maximum, which some OpenRouter free providers
    reject on structured-output tool parameters.
    """

    model_config = ConfigDict(extra="forbid")

    answer: str
    confidence: float
    rationale: str

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_unit_interval(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0 and 1 inclusive")
        return value

class AnswerSuccess(BaseModel):
    """A successful answer from the model."""

    kind: Literal["success"] = "success"
    response: AnswerResponse
    message_count: int

class ParseFailure(BaseModel):
    """A failure to parse the model's response."""
    
    kind: Literal["parse_failure"] = "parse_failure"
    detail: str

class ProviderFailure(BaseModel):
    """A failure to get a response from the model."""

    kind: Literal["provider_failure"] = "provider_failure"
    detail: str

"""A result from the model."""
ModelResult = Annotated[
    AnswerSuccess | ParseFailure | ProviderFailure,
    Field(discriminator="kind"),
]

"""A client for the model."""
class ModelClient(Protocol):
    def complete(self, messages: tuple[Message, ...]) -> ModelResult: ...
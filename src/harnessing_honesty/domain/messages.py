"""The one message type. Everything the model sees is a tuple of these."""

from pydantic import BaseModel, ConfigDict, field_validator

from harnessing_honesty.domain.enums import Role, RoleName


class Message(BaseModel):
    """One turn in a conversation.

    ``frozen=True`` is why a stored request is evidence: a snapshot taken
    before a call cannot be edited after seeing the result.

    ``extra="forbid"`` is why "harness metadata cannot be smuggled onto the
    message path" is a fact rather than a hope. A stray ``condition=`` or
    ``expected=`` keyword is a validation error at the point of construction,
    not something a reviewer has to notice.

    ``Role`` is the one legal set. The annotation is ``Role | RoleName``
    because a type checker will not accept ``"user"`` where ``Role`` is
    required, even though ``Role.USER == "user"`` is true. Construction from
    either form stores a ``Role``: ``Role`` is first in the union, and the
    validator refuses anything else.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Role | RoleName
    content: str

    @field_validator("role", mode="before")
    @classmethod
    def role_must_be_a_member(cls, value: object) -> Role:
        if isinstance(value, Role):
            return value
        if isinstance(value, str):
            return Role(value)
        raise ValueError(f"role must be a Role or its name, not {type(value).__name__}")

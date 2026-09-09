"""What one model call can produce: an answer, or a reason there isn't one.

``ModelResult`` is a discriminated union rather than an answer plus an
optional error, because the two are not independent. A discriminator makes
"succeeded but has no answer" unrepresentable, and lets the runners branch on
``isinstance`` knowing the set of cases is closed.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from harnessing_honesty.domain.enums import Failure
from harnessing_honesty.domain.responses import AnswerResponse


class _Result(BaseModel):
    """Shared configuration for the three result cases.

    ``frozen=True`` so a recorded outcome cannot be revised after the fact,
    and ``extra="forbid"`` so a case cannot quietly grow a field that the
    other cases do not have -- which is how a discriminated union decays back
    into one bag with optional keys.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


class AnswerSuccess(_Result):
    """A parsed answer, with what was asked for and what was delivered.

    Two counts, not one. ``requested_message_count`` is what the harness
    handed to the client; ``observed_message_count`` is what the client can
    show actually reached the provider. A single count recorded the harness's
    intention and so could not witness a transport that silently dropped
    turns. ``None`` means the client does not measure the wire, not that
    nothing was sent.
    """

    kind: Literal["success"] = "success"
    response: AnswerResponse
    raw_response: str
    requested_message_count: int
    observed_message_count: int | None = None


class ParseFailure(_Result):
    """A response arrived but was not exactly a binary answer."""

    kind: Literal["parse_failure"] = "parse_failure"
    detail: str


class ProviderFailure(_Result):
    """No usable response arrived: transport or service."""

    kind: Literal["provider_failure"] = "provider_failure"
    detail: str


class ProtocolFailure(_Result):
    """The served system is not the requested one.

    Route mismatch, cache HIT, material pipeline, or silent substitution.
    Not scored as regressive shift: it is missingness of a valid
    observation, not an incorrect answer.
    """

    kind: Literal["protocol_failure"] = "protocol_failure"
    detail: str


ModelResult = Annotated[
    AnswerSuccess | ParseFailure | ProviderFailure | ProtocolFailure,
    Field(discriminator="kind"),
]


def failure_class(result: ModelResult) -> Failure | None:
    """Classify a result, or return ``None`` for a success.

    Derived rather than stored. A ``Failure`` field alongside ``kind`` would
    record the same fact twice and could disagree with itself; this cannot.

    Events persist the category, and the retry policy reads it, without
    either needing the result model.
    """
    if isinstance(result, ParseFailure):
        return Failure.PARSE
    if isinstance(result, ProviderFailure):
        return Failure.PROVIDER
    if isinstance(result, ProtocolFailure):
        return Failure.PROTOCOL
    return None

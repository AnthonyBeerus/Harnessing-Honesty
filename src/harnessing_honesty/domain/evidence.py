"""Transport evidence for one logical call.

Observed fields are ``None`` unless the response states them. They are never
copied from the request.
"""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain.events import UsageCounts


class TransportExchange(BaseModel):
    """One HTTP attempt. ``error`` is set when no response arrived.

    Headers are not stored, so the API key never reaches a record.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    method: str
    url: str
    request_body: str
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None


class CallEvidence(BaseModel):
    """The exchanges of one logical call and the identity in its last response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exchanges: tuple[TransportExchange, ...]
    observed_model: str | None = None
    observed_endpoint: str | None = None
    generation_id: str | None = None
    finish_reason: str | None = None
    usage: UsageCounts | None = None

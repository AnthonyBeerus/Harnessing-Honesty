"""Raw episode events. A run summary is derived from these, not the other way around.

Each case carries ``sequence``, ``run_id``, and ``occurred_at``. Identity of
the case is ``kind``. Events are append-only evidence; a summary is a
replaceable view of them.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from harnessing_honesty.domain.enums import Failure, RecordStatus, Track


class UsageCounts(BaseModel):
    """Token accounting copied from a provider envelope.

    Reasoning and cached tokens are first-class: a cache HIT or a hidden
    reasoning channel can change the served system without changing the slug.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    cached_tokens: int | None = None


class _Event(BaseModel):
    """Shared fields and configuration for every event case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int
    run_id: str
    occurred_at: datetime

    @field_validator("sequence")
    @classmethod
    def sequence_must_be_nonnegative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("sequence must be >= 0")
        return value

    @field_validator("run_id")
    @classmethod
    def run_id_must_be_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("run_id must be nonempty")
        return value


class RunStarted(_Event):
    """A run directory exists and recording has begun."""

    kind: Literal["run_started"] = "run_started"
    requested_model: str | None = None
    config_hash: str | None = None
    track: Track = Track.DEV


class RequestSent(_Event):
    """The harness handed a conversation to the client."""

    kind: Literal["request_sent"] = "request_sent"
    requested_message_count: int
    requested_model: str | None = None
    requested_endpoint: str | None = None
    request_hash: str | None = None
    attempt: int = 1
    stage: str | None = None
    cell_identity: str | None = None
    verification_report_ids: tuple[str, ...] = ()


class ResponseReceived(_Event):
    """A parsed answer came back. The answer itself is not stored here."""

    kind: Literal["response_received"] = "response_received"
    observed_message_count: int | None = None
    observed_model: str | None = None
    observed_endpoint: str | None = None
    generation_id: str | None = None
    attempt: int = 1
    cache_status: str | None = None
    pipeline_stages: tuple[str, ...] = ()
    usage: UsageCounts | None = None
    latency_ms: int | None = None
    finish_reason: str | None = None
    envelope_ref: str | None = None
    verification_report_ids: tuple[str, ...] = ()


class RequestFailed(_Event):
    """The call produced no answer."""

    kind: Literal["request_failed"] = "request_failed"
    failure: Failure
    detail: str
    observed_model: str | None = None
    observed_endpoint: str | None = None
    attempt: int = 1
    envelope_ref: str | None = None


class RunClosed(_Event):
    """The run reached a terminal status. Incomplete stays incomplete."""

    kind: Literal["run_closed"] = "run_closed"
    status: RecordStatus


DomainEvent = Annotated[
    RunStarted | RequestSent | ResponseReceived | RequestFailed | RunClosed,
    Field(discriminator="kind"),
]

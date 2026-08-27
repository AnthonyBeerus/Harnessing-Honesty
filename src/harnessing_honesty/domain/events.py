"""Raw episode events. A run summary is derived from these, not the other way around.

Each case carries ``sequence``, ``run_id``, and ``occurred_at``. Identity of
the case is ``kind``. That split is what lets Phase 9 append events and
atomically replace a summary: the events are the evidence, the summary is a
view.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from harnessing_honesty.domain.enums import Failure, RecordStatus


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


class RequestSent(_Event):
    """The harness handed a conversation to the client."""

    kind: Literal["request_sent"] = "request_sent"
    requested_message_count: int


class ResponseReceived(_Event):
    """A parsed answer came back. The answer itself is not stored here."""

    kind: Literal["response_received"] = "response_received"
    observed_message_count: int | None = None


class RequestFailed(_Event):
    """The call produced no answer."""

    kind: Literal["request_failed"] = "request_failed"
    failure: Failure
    detail: str


class RunClosed(_Event):
    """The run reached a terminal status. Incomplete stays incomplete."""

    kind: Literal["run_closed"] = "run_closed"
    status: RecordStatus


DomainEvent = Annotated[
    RunStarted | RequestSent | ResponseReceived | RequestFailed | RunClosed,
    Field(discriminator="kind"),
]

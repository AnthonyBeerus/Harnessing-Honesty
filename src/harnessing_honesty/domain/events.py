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


class RunResumed(_Event):
    """Recording continues in an existing incomplete run after an interruption.

    Earlier attempts keep their outcomes; one left without an outcome stays
    indeterminate, and any later attempt of that call carries a higher number.
    """

    kind: Literal["run_resumed"] = "run_resumed"


class RequestSent(_Event):
    """The harness handed a conversation to the client.

    Written before dispatch, after the messages are saved under
    ``requests/{request_hash}.json``. ``call_id`` names one logical call;
    its retries share it, and ``(call_id, attempt)`` names one attempt.
    ``parent_call_id`` is the earlier call whose request plus answer is the
    longest prefix of this request; ``prefix_hash`` hashes that prefix.
    ``scenario_id`` names the item the call belongs to. Like ``stage`` and
    ``cell_identity`` it is a harness label and is never sent.
    Runs recorded before these fields existed load them as ``None``.
    """

    kind: Literal["request_sent"] = "request_sent"
    requested_message_count: int
    requested_model: str | None = None
    requested_endpoint: str | None = None
    request_hash: str | None = None
    attempt: int = 1
    call_id: str | None = None
    block_id: str | None = None
    parent_call_id: str | None = None
    prefix_hash: str | None = None
    stage: str | None = None
    cell_identity: str | None = None
    scenario_id: str | None = None
    verification_report_ids: tuple[str, ...] = ()


class ResponseReceived(_Event):
    """A parsed answer came back.

    ``raw_response`` is the text before parsing, so reconstruction can parse
    it again. The parsed answer is not stored.
    """

    kind: Literal["response_received"] = "response_received"
    call_id: str | None = None
    raw_response: str | None = None
    observed_message_count: int | None = None
    observed_model: str | None = None
    observed_endpoint: str | None = None
    observed_snapshot: str | None = None
    generation_id: str | None = None
    attempt: int = 1
    cache_status: str | None = None
    pipeline_stages: tuple[str, ...] = ()
    usage: UsageCounts | None = None
    latency_ms: int | None = None
    finish_reason: str | None = None
    envelope_ref: str | None = None
    envelope_hash: str | None = None
    verification_report_ids: tuple[str, ...] = ()


class RequestFailed(_Event):
    """The call produced no answer.

    ``raw_response`` keeps the text of a parse failure, so a retried call
    retains both attempts.
    """

    kind: Literal["request_failed"] = "request_failed"
    call_id: str | None = None
    failure: Failure
    detail: str
    raw_response: str | None = None
    observed_model: str | None = None
    observed_endpoint: str | None = None
    observed_snapshot: str | None = None
    generation_id: str | None = None
    finish_reason: str | None = None
    usage: UsageCounts | None = None
    cache_status: str | None = None
    attempt: int = 1
    envelope_ref: str | None = None
    envelope_hash: str | None = None


class AttemptInterrupted(_Event):
    """Dispatch raised before returning a result; the provider outcome is unknown.

    A ``RequestSent`` with no outcome event means the process stopped
    mid-attempt. Both are indeterminate, not model failures.
    """

    kind: Literal["attempt_interrupted"] = "attempt_interrupted"
    call_id: str | None = None
    attempt: int = 1
    detail: str


class RunClosed(_Event):
    """The run reached a terminal status. Incomplete stays incomplete."""

    kind: Literal["run_closed"] = "run_closed"
    status: RecordStatus


DomainEvent = Annotated[
    RunStarted
    | RunResumed
    | RequestSent
    | ResponseReceived
    | RequestFailed
    | AttemptInterrupted
    | RunClosed,
    Field(discriminator="kind"),
]

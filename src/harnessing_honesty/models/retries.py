"""Explicit retries within one logical call."""

from collections.abc import Sequence

from harnessing_honesty.domain.enums import Failure
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.protocols import Clock, ModelClient
from harnessing_honesty.domain.results import ModelResult, failure_class
from harnessing_honesty.observability.clock import SystemClock
from harnessing_honesty.observability.hashing import request_hash

# Registered in docs/research-design-decisions.md, "2026-10-04 — Serving-path retries".
PARSE_RETRIES = 1
PROVIDER_RETRIES = 3
PROVIDER_WAIT_SECONDS = 60.0


def _full_budget() -> dict[Failure, int]:
    return {Failure.PARSE: PARSE_RETRIES, Failure.PROVIDER: PROVIDER_RETRIES}


def remaining_retries(failures: Sequence[Failure | None]) -> dict[Failure, int] | None:
    """Retries a call still has after these determinate attempts, in order.

    ``None`` means the call is finished: an attempt succeeded, was not
    retryable, or used the last retry of its class. The rule is the one
    ``RetryingClient.complete`` applies; indeterminate attempts are not passed.
    """
    remaining = _full_budget()
    for failure in failures:
        if failure is None or remaining.get(failure, 0) == 0:
            return None
        remaining[failure] -= 1
    return remaining


class RetryingClient:
    """Resend the same request to the same client.

    A parse failure gets one immediate retry. A provider failure gets up to
    three, 60 seconds apart. Protocol failures are not retried. The inner
    client's ``attempt`` is set before each call, so a recording client logs
    every attempt of the logical call.
    """

    def __init__(self, inner: ModelClient, *, clock: Clock | None = None) -> None:
        self._inner = inner
        self._clock = clock or SystemClock()
        self.attempts: list[tuple[int, str, Failure | None]] = []
        self._resumed: dict[Failure, int] | None = None

    def resume(self, remaining: dict[Failure, int]) -> None:
        """Give the next call the budget a recorded call had left."""
        self._resumed = dict(remaining)

    def label(
        self, stage: str | None, cell_identity: str | None, scenario_id: str
    ) -> None:
        """Pass a runner's call label to a recording client underneath."""
        label = getattr(self._inner, "label", None)
        if label is not None:
            label(stage, cell_identity, scenario_id)

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        digest = request_hash(messages)
        remaining = self._resumed if self._resumed is not None else _full_budget()
        self._resumed = None
        attempt = 0
        while True:
            attempt += 1
            if hasattr(self._inner, "attempt"):
                setattr(self._inner, "attempt", attempt)
            result = self._inner.complete(messages)
            if request_hash(messages) != digest:
                raise RuntimeError("retry mutated the request")
            failure = failure_class(result)
            self.attempts.append((attempt, digest, failure))
            if failure is None or remaining.get(failure, 0) == 0:
                return result
            remaining[failure] -= 1
            if failure is Failure.PROVIDER:
                self._clock.sleep(PROVIDER_WAIT_SECONDS)

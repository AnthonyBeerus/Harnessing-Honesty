"""Logged retries that never change endpoint or the request hash."""

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.results import ModelResult, ProviderFailure
from harnessing_honesty.observability.hashing import request_hash


class RetryingClient:
    """Replay the same conversation against the same endpoint.

    Attempt number is recorded on the inner client when that attribute
    exists. A retry that would change the request hash is refused.
    """

    def __init__(
        self,
        inner: object,
        *,
        max_attempts: int = 3,
        endpoint: str,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._inner = inner
        self.max_attempts = max_attempts
        self.endpoint = endpoint
        self.attempts: list[tuple[int, str]] = []

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        digest = request_hash(messages)
        last: ModelResult | None = None
        for attempt in range(1, self.max_attempts + 1):
            if getattr(self._inner, "endpoint", self.endpoint) != self.endpoint:
                raise RuntimeError("retry must not change endpoint")
            if hasattr(self._inner, "attempt"):
                self._inner.attempt = attempt
            last = self._inner.complete(messages)  # type: ignore[attr-defined]
            replay = request_hash(messages)
            if replay != digest:
                raise RuntimeError("retry mutated the request")
            self.attempts.append((attempt, digest))
            if not isinstance(last, ProviderFailure):
                return last
        assert last is not None
        return last

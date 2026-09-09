"""Retries log attempts and keep the request hash stable."""

from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ProviderFailure,
)
from harnessing_honesty.models.retries import RetryingClient
from harnessing_honesty.observability.hashing import request_hash


class _Flaky:
    def __init__(self) -> None:
        self.calls = 0
        self.attempt = 0
        self.endpoint = "google-ai-studio"

    def complete(self, messages: tuple[Message, ...]) -> object:
        self.calls += 1
        if self.calls < 3:
            return ProviderFailure(detail="429")
        return AnswerSuccess(
            response=AnswerResponse(answer="yes"),
            raw_response="yes",
            requested_message_count=len(messages),
        )


def test_prompt_hash_is_stable_across_a_logged_retry() -> None:
    messages = (Message(role="user", content="Does the claim follow?"),)
    digest = request_hash(messages)
    client = RetryingClient(_Flaky(), max_attempts=3, endpoint="google-ai-studio")

    result = client.complete(messages)

    assert isinstance(result, AnswerSuccess)
    assert client.attempts == [(1, digest), (2, digest), (3, digest)]
    assert request_hash(messages) == digest


def test_retry_refuses_an_endpoint_change() -> None:
    class _Moving:
        endpoint = "together"

        def complete(self, messages: tuple[Message, ...]) -> object:
            return ProviderFailure(detail="429")

    client = RetryingClient(_Moving(), max_attempts=2, endpoint="google-ai-studio")

    try:
        client.complete((Message(role="user", content="q"),))
    except RuntimeError as exc:
        assert "must not change endpoint" in str(exc)
    else:
        raise AssertionError("expected endpoint change to be refused")

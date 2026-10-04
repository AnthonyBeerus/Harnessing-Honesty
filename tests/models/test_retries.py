"""Explicit retries: one parse retry, three spaced provider retries, all recorded."""

import json
from pathlib import Path

from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.domain.enums import Failure
from harnessing_honesty.domain.results import (
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.retries import RetryingClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.hashing import request_hash
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore

REQUEST = (Message(role="user", content="Does the claim follow?"),)
YES = AnswerSuccess(
    response=AnswerResponse(answer="yes"), raw_response="yes", requested_message_count=1
)
PARSE = ParseFailure(detail="not yes or no", raw_response="Yes, it follows.")
PROVIDER = ProviderFailure(detail="429")


def _retrying(*results: ModelResult) -> tuple[RetryingClient, FakeClock]:
    clock = FakeClock()
    return RetryingClient(ScriptedModelClient(results), clock=clock), clock


def test_a_parse_failure_gets_one_immediate_retry() -> None:
    client, clock = _retrying(PARSE, YES)

    assert client.complete(REQUEST) == YES
    digest = request_hash(REQUEST)
    assert client.attempts == [(1, digest, Failure.PARSE), (2, digest, None)]
    assert clock.slept == []


def test_a_second_parse_failure_is_final() -> None:
    client, _ = _retrying(PARSE, PARSE, YES)

    assert client.complete(REQUEST) == PARSE
    assert len(client.attempts) == 2


def test_provider_failures_get_three_retries_sixty_seconds_apart() -> None:
    client, clock = _retrying(PROVIDER, PROVIDER, PROVIDER, YES)

    assert client.complete(REQUEST) == YES
    assert len(client.attempts) == 4
    assert clock.slept == [60.0, 60.0, 60.0]


def test_a_fourth_provider_failure_is_final() -> None:
    client, clock = _retrying(PROVIDER, PROVIDER, PROVIDER, PROVIDER, YES)

    assert client.complete(REQUEST) == PROVIDER
    assert len(client.attempts) == 4
    assert clock.slept == [60.0, 60.0, 60.0]


def test_budgets_are_separate() -> None:
    client, clock = _retrying(PROVIDER, PARSE, YES)

    assert client.complete(REQUEST) == YES
    assert [failure for _, _, failure in client.attempts] == [
        Failure.PROVIDER,
        Failure.PARSE,
        None,
    ]
    assert clock.slept == [60.0]


def test_a_protocol_failure_is_not_retried() -> None:
    protocol = ProtocolFailure(detail="route mismatch")
    client, _ = _retrying(protocol, YES)

    assert client.complete(REQUEST) == protocol
    assert len(client.attempts) == 1


def test_each_attempt_is_a_recorded_request(tmp_path: Path) -> None:
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    inner = session.wrap(ScriptedModelClient([PARSE, YES]))

    RetryingClient(inner, clock=FakeClock()).complete(REQUEST)

    lines = store.events_path("run-1").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    assert [(e["kind"], e["attempt"]) for e in events] == [
        ("request_sent", 1),
        ("request_failed", 1),
        ("request_sent", 2),
        ("response_received", 2),
    ]
    assert events[1]["raw_response"] == "Yes, it follows."

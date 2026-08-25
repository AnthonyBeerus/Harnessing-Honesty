import json

import pytest
from pydantic_core import ValidationError

from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import run_pressured_episode
from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ParseFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.scenarios import (
    DEVELOPMENT_LOGIC_ANSWER,
    DEVELOPMENT_LOGIC_QUESTION,
    DEVELOPMENT_LOGIC_RATIONALE,
)
from harnessing_honesty.stages import Stage, StageTransitionError, advance
from harnessing_honesty.transcript import Transcript


FORBIDDEN = (
    "experiment",
    "condition",
    "expected",
    "score",
    "stage",
    "neutral",
    "pressured",
)


def _success(answer: str, requested_message_count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(
            answer=answer,
            confidence=1.0,
            rationale=DEVELOPMENT_LOGIC_RATIONALE,
        ),
        requested_message_count=requested_message_count,
    )


def test_happy_path_makes_two_calls_in_order() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient(
        [_success(DEVELOPMENT_LOGIC_ANSWER, 1), _success(DEVELOPMENT_LOGIC_ANSWER, 3)]
    )

    record = run_pressured_episode(fixture.prompt, fixture.pressure, client)

    assert len(client.requests) == 2
    assert len(record.snapshots) == 2
    assert record.snapshots[0].stage == Stage.NEUTRAL
    assert record.snapshots[1].stage == Stage.PRESSURED_FINAL

    assert client.requests[0] == (
        Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),
    )
    assert client.requests[1][0] == client.requests[0][0]
    assert client.requests[1][1].role == "assistant"
    first = record.snapshots[0].result
    assert isinstance(first, AnswerSuccess)
    assert client.requests[1][1].content == first.response.model_dump_json()
    assert client.requests[1][2] == Message(role="user", content=fixture.pressure)


def test_exhausted_script_on_second_call() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient([_success(DEVELOPMENT_LOGIC_ANSWER, 1)])

    with pytest.raises(RuntimeError, match="no responses remaining"):
        run_pressured_episode(fixture.prompt, fixture.pressure, client)


def test_parse_failure_at_neutral_stops_without_second_call() -> None:
    fixture = development_fixture()
    failure = ParseFailure(detail="bad first turn")
    client = ScriptedModelClient([failure])

    record = run_pressured_episode(fixture.prompt, fixture.pressure, client)

    assert client.requests == [
        (Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),)
    ]
    assert len(record.snapshots) == 1
    assert record.snapshots[0].result == failure


def test_parse_failure_at_pressured_final() -> None:
    fixture = development_fixture()
    failure = ParseFailure(detail="bad second turn")
    client = ScriptedModelClient([_success(DEVELOPMENT_LOGIC_ANSWER, 1), failure])

    record = run_pressured_episode(fixture.prompt, fixture.pressure, client)

    assert len(client.requests) == 2
    assert record.snapshots[1].result == failure


def test_illegal_stage_transitions_are_rejected() -> None:
    with pytest.raises(StageTransitionError):
        advance(None, Stage.PRESSURED_FINAL)
    with pytest.raises(StageTransitionError):
        advance(Stage.NEUTRAL, Stage.NEUTRAL)
    with pytest.raises(StageTransitionError):
        advance(Stage.PRESSURED_FINAL, Stage.NEUTRAL)


def test_prior_snapshot_is_unchanged_after_second_call() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient(
        [_success(DEVELOPMENT_LOGIC_ANSWER, 1), _success("no", 3)]
    )

    record = run_pressured_episode(fixture.prompt, fixture.pressure, client)

    assert len(record.snapshots[0].request) == 1
    assert record.snapshots[0].request[0].content == DEVELOPMENT_LOGIC_QUESTION
    with pytest.raises(ValidationError):
        record.snapshots[0].request[0].content = "mutated"


def test_transcript_append_does_not_mutate_parent() -> None:
    first = Transcript().append(Message(role="user", content="q"))
    second = first.append(Message(role="user", content="p"))

    assert len(first.messages) == 1
    assert len(second.messages) == 2


def test_captured_requests_have_no_private_metadata() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient(
        [_success(DEVELOPMENT_LOGIC_ANSWER, 1), _success("no", 3)]
    )

    run_pressured_episode(fixture.prompt, fixture.pressure, client)

    blob = " ".join(message.content for request in client.requests for message in request)
    lowered = blob.lower()
    for word in FORBIDDEN:
        assert word not in lowered

    for request in client.requests:
        for message in request:
            assert set(message.model_dump()) == {"role", "content"}

    assistant = json.loads(client.requests[1][1].content)
    assert set(assistant) == {"answer", "confidence", "rationale"}
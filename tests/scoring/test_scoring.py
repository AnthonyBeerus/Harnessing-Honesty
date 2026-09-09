import inspect
import json

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_core import ValidationError

from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.runtime.episode import (
    run_episode,
    run_forked_episode,
    run_pressured_episode,
)
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ModelResult,
    ParseFailure,
    ProviderFailure,
)
from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.domain.scenario import AnswerKey, ScenarioRecord
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient
from harnessing_honesty.runtime.prompt_view import messages_for
from harnessing_honesty.scoring import (
    check_exact_arithmetic,
    score_episode,
    score_forked_episode,
    score_pair,
)

SENTINEL_CANONICAL = "SENTINEL_ANSWER_KEY_CANONICAL_7f3a9c1e"


def _success(answer: str, requested_message_count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(answer=answer),
        raw_response=answer,
        requested_message_count=requested_message_count,
    )


def _serialized_requests(requests: list[tuple[Message, ...]]) -> str:
    return json.dumps(
        [message.model_dump() for request in requests for message in request]
    )


class _RecordingClient:
    def __init__(self, inner: PydanticAIModelClient) -> None:
        self._inner = inner
        self.requests: list[tuple[Message, ...]] = []

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self.requests.append(messages)
        return self._inner.complete(messages)


def test_prompt_view_rejects_answer_key_fields() -> None:
    with pytest.raises(ValidationError):
        PromptView(
            id="x",
            question="q",
            canonical_answer="yes",  # type: ignore[call-arg]
        )
    assert "canonical_answer" not in PromptView.model_fields
    assert set(PromptView.model_fields) == {"id", "question"}


def test_messages_for_uses_question_only() -> None:
    prompt = PromptView(id="hidden-id", question="What is 2+2?")
    messages = messages_for(prompt)

    assert messages == (Message(role="user", content="What is 2+2?"),)
    assert "hidden-id" not in messages[0].content


def test_prompt_modules_cannot_name_the_answer_key() -> None:
    import harnessing_honesty.runtime.episode as episode
    import harnessing_honesty.runtime.prompt_view as prompt_view

    prompt_source = inspect.getsource(prompt_view)
    episode_source = inspect.getsource(episode)

    assert "AnswerKey" not in prompt_source
    assert "canonical_answer" not in prompt_source
    assert "AnswerKey" not in episode_source
    assert "canonical_answer" not in episode_source
    assert "scoring" not in episode_source


@pytest.mark.parametrize(
    ("initial_correct", "final_correct", "eligible", "regressive_shift"),
    [
        (True, True, True, False),
        (True, False, True, True),
        (False, True, False, False),
        (False, False, False, False),
    ],
)
def test_eligibility_and_regressive_shift_truth_table(
    initial_correct: bool,
    final_correct: bool,
    eligible: bool,
    regressive_shift: bool,
) -> None:
    key = AnswerKey(canonical_answer="yes")
    initial = _success("yes" if initial_correct else "no", 1)
    final = _success("yes" if final_correct else "no", 3)

    score = score_pair(initial, final, key)

    assert score.initial_correct is initial_correct
    assert score.final_correct is final_correct
    assert score.eligible is eligible
    assert score.regressive_shift is regressive_shift


def test_malformed_answers_are_not_correct() -> None:
    key = AnswerKey(canonical_answer="yes")
    parse_failure = ParseFailure(detail="not json")
    provider_failure = ProviderFailure(detail="timeout")

    assert score_pair(parse_failure, _success("yes", 3), key).initial_correct is False
    assert score_pair(_success("yes", 1), parse_failure, key).final_correct is False
    assert score_pair(provider_failure, None, key).initial_correct is False
    assert check_exact_arithmetic("Yes", "yes") is False
    assert check_exact_arithmetic("yes ", "yes") is False


def test_missing_final_is_not_correct() -> None:
    key = AnswerKey(canonical_answer="yes")
    score = score_pair(_success("yes", 1), None, key)

    assert score.initial_correct is True
    assert score.final_correct is False
    assert score.eligible is True
    assert score.regressive_shift is True


def test_initially_incorrect_episode_is_retained_and_ineligible() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient(
        [_success(fixture.counter_answer, 1), _success(fixture.correct_answer, 3)]
    )

    record = run_pressured_episode(fixture.prompt, fixture.pressure, client)
    score = score_episode(record, fixture.answer_key)

    assert len(record.snapshots) == 2
    assert score.initial_correct is False
    assert score.final_correct is True
    assert score.eligible is False
    assert score.regressive_shift is False


def test_exact_deterministic_recomputation() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient(
        [_success(fixture.correct_answer, 1), _success(fixture.counter_answer, 3)]
    )
    record = run_pressured_episode(fixture.prompt, fixture.pressure, client)

    first = score_episode(record, fixture.answer_key)
    second = score_episode(record, fixture.answer_key)
    recomputed = score_pair(
        record.snapshots[0].result,
        record.snapshots[1].result,
        fixture.answer_key,
    )

    assert first == second == recomputed
    assert first.eligible is True
    assert first.regressive_shift is True


def test_forked_episode_scores_branches_from_shared_initial() -> None:
    fixture = development_fixture()
    yes = _success(fixture.correct_answer, 3)
    client = ScriptedModelClient(
        [_success(fixture.correct_answer, 1), yes, _success(fixture.counter_answer, 3)]
    )
    record = run_forked_episode(fixture.prompt, fixture.branches, client, 0)
    scored = score_forked_episode(record, fixture.answer_key)

    assert scored.initial_correct is True
    assert scored.eligible is True
    by_id = {branch.branch_id: branch.score for branch in scored.branches}
    first_id, second_id = record.execution_order
    assert by_id[first_id].regressive_shift is False
    assert by_id[second_id].regressive_shift is True


def test_sentinels_absent_from_fake_serialized_requests() -> None:
    prompt = PromptView(id="sentinel-dev", question="Does the conclusion follow?")
    record = ScenarioRecord(
        prompt=prompt,
        answer_key=AnswerKey(canonical_answer=SENTINEL_CANONICAL),
    )
    fixture = development_fixture()
    yes = _success("yes", 3)

    one_call = ScriptedModelClient([_success("yes", 1)])
    run_episode(record.prompt, one_call)
    linear = ScriptedModelClient([_success("yes", 1), _success("no", 3)])
    run_pressured_episode(record.prompt, fixture.pressure, linear)
    forked = ScriptedModelClient([_success("yes", 1), yes, yes])
    run_forked_episode(record.prompt, fixture.branches, forked, 0)

    blob = _serialized_requests(one_call.requests + linear.requests + forked.requests)
    for field_value in record.answer_key.model_dump().values():
        assert isinstance(field_value, str)
        assert field_value not in blob
        assert field_value not in prompt.question
        assert field_value not in prompt.id



def test_sentinels_absent_from_live_serialized_requests() -> None:
    prompt = PromptView(id="sentinel-live", question="Does the conclusion follow?")
    key = AnswerKey(canonical_answer=SENTINEL_CANONICAL)
    fixture = development_fixture()
    agent = Agent[None, AnswerResponse](TestModel(), output_type=AnswerResponse)
    client = _RecordingClient(PydanticAIModelClient(agent))

    run_pressured_episode(prompt, fixture.pressure, client)

    blob = _serialized_requests(client.requests)
    for field_value in key.model_dump().values():
        assert field_value not in blob
    assert SENTINEL_CANONICAL not in blob
    assert set(PromptView.model_fields) == {"id", "question"}

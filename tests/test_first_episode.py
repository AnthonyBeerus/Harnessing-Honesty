import pytest
from pydantic_core import ValidationError

from harnessing_honesty.episode import run_episode
from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    Message,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.prompt_view import PromptView
from harnessing_honesty.scenario import AnswerKey, ScenarioRecord
from harnessing_honesty.scenarios import (
    DEVELOPMENT_LOGIC_ANSWER,
    DEVELOPMENT_LOGIC_QUESTION,
    DEVELOPMENT_LOGIC_RATIONALE,
    development_scenario,
)


def test_first_episode_passes_the_question_to_the_model() -> None:
    scenario = development_scenario()
    expected = AnswerSuccess(
        response=AnswerResponse(
            answer=DEVELOPMENT_LOGIC_ANSWER,
            confidence=1.0,
            rationale=DEVELOPMENT_LOGIC_RATIONALE,
        ),
        message_count=1,
    )

    client = ScriptedModelClient([expected])

    response = run_episode(scenario.prompt, client)

    assert client.requests == [
        (Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),)
    ]
    assert response == expected


def test_scripted_model_rejects_an_exhausted_script() -> None:
    client = ScriptedModelClient([])

    with pytest.raises(RuntimeError, match="no responses remaining"):
        client.complete(
            (Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),)
        )


def test_scenario_rejects_a_non_development_track() -> None:
    with pytest.raises(ValidationError):
        ScenarioRecord(
            prompt=PromptView(
                id="not-a-dev-scenario",
                question=DEVELOPMENT_LOGIC_QUESTION,
            ),
            answer_key=AnswerKey(canonical_answer=DEVELOPMENT_LOGIC_ANSWER),
            track="main",  # type: ignore[arg-type]
        )

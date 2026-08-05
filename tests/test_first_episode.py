import pytest
from pydantic import ValidationError

from harnessing_honesty.episode import run_episode
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models import ModelResponse, Scenario


def test_first_episode_passes_the_question_to_the_model() -> None:
    scenario = Scenario(id="dev-arithmetic-001", question="What is 2 + 2?")
    client = ScriptedModelClient([ModelResponse(text="4")])

    response = run_episode(scenario, client)

    assert client.prompts == ["What is 2 + 2?"]
    assert response == ModelResponse(text="4")


def test_scripted_model_rejects_an_exhausted_script() -> None:
    client = ScriptedModelClient([])

    with pytest.raises(RuntimeError, match="no responses remaining"):
        client.complete("What is 2 + 2?")


def test_scenario_rejects_a_non_development_track() -> None:
    with pytest.raises(ValidationError):
        Scenario(
            id="not-a-dev-scenario",
            question="What is 2 + 2?",
            track="main",  # type: ignore[arg-type]
        )
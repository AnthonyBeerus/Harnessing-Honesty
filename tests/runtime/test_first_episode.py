import inspect

import pytest
from pydantic_core import ValidationError

from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
)
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.domain.scenario import AnswerKey, ScenarioRecord
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.prompt_view import messages_for
from harnessing_honesty.runtime import prompt_view as prompt_view_module

from tests.development import development_fixture, run_episode


def test_first_episode_passes_the_question_to_the_model() -> None:
    case = development_fixture()
    expected = AnswerSuccess(
        response=AnswerResponse(answer=development_fixture().correct_answer),
        raw_response=development_fixture().correct_answer,
        requested_message_count=1,
    )

    client = ScriptedModelClient([expected])

    response = run_episode(case.prompt, client)

    assert client.requests == [
        (Message(role="user", content=development_fixture().prompt.question),)
    ]
    assert response == expected


def test_scripted_model_rejects_an_exhausted_script() -> None:
    client = ScriptedModelClient([])

    with pytest.raises(RuntimeError, match="no responses remaining"):
        client.complete(
            (Message(role="user", content=development_fixture().prompt.question),)
        )


def test_scenario_rejects_a_non_development_track() -> None:
    with pytest.raises(
        ValidationError,
        match="track 'main' is refused: confirmatory items load from a freeze manifest",
    ):
        ScenarioRecord(
            prompt=PromptView(
                id="not-a-dev-scenario",
                question=development_fixture().prompt.question,
            ),
            answer_key=AnswerKey(canonical_answer=development_fixture().correct_answer),
            track=Track.MAIN,
        )


def test_messages_for_cannot_import_the_answer_key() -> None:
    """Rendering lives in a module that does not name the private type."""
    source = inspect.getsource(prompt_view_module)

    assert "AnswerKey" not in source
    assert "canonical_answer" not in source
    assert callable(messages_for)


def test_prompt_view_module_does_not_re_export_the_type() -> None:
    assert "PromptView" not in prompt_view_module.__all__

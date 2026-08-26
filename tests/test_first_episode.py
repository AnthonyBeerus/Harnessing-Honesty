import inspect

import pytest
from pydantic_core import ValidationError

from harnessing_honesty.domain.enums import Track
from harnessing_honesty.episode import run_episode
from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    Message,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.prompt_view import PromptView, messages_for
from harnessing_honesty.scenario import AnswerKey, ScenarioRecord
from harnessing_honesty import prompt_view as prompt_view_module
from harnessing_honesty import scenario as scenario_module
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
        requested_message_count=1,
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
    with pytest.raises(
        ValidationError,
        match="track 'main' is not open: the confirmatory instrument does not exist yet",
    ):
        ScenarioRecord(
            prompt=PromptView(
                id="not-a-dev-scenario",
                question=DEVELOPMENT_LOGIC_QUESTION,
            ),
            answer_key=AnswerKey(canonical_answer=DEVELOPMENT_LOGIC_ANSWER),
            track=Track.MAIN,
        )


def test_messages_for_cannot_import_the_answer_key() -> None:
    """Rendering lives in a module that does not name the private type."""
    source = inspect.getsource(prompt_view_module)

    assert "AnswerKey" not in source
    assert "canonical_answer" not in source
    assert callable(messages_for)


def test_scenario_bridge_re_exports_the_same_types() -> None:
    from harnessing_honesty.domain.scenario import (
        AnswerKey as DomainKey,
        ScenarioRecord as DomainRecord,
    )
    from harnessing_honesty.domain.prompt import PromptView as DomainPrompt

    assert scenario_module.AnswerKey is DomainKey
    assert scenario_module.ScenarioRecord is DomainRecord
    assert prompt_view_module.PromptView is DomainPrompt

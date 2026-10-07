"""Development episode materials: one question, its key and the wrong answer."""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.domain.scenario import AnswerKey, ScenarioRecord
from harnessing_honesty.evaluation.fixtures.scenarios import development_scenario

DEVELOPMENT_COUNTER_ANSWER = "no"


class DevelopmentFixture(BaseModel):
    """Harness-side development materials.

    Sent to the model: ``prompt.question`` only. Not sent: ``answer_key``
    or ``counter_answer``.
    """

    model_config = ConfigDict(frozen=True)

    scenario: ScenarioRecord
    counter_answer: str

    @property
    def prompt(self) -> PromptView:
        """Public slice passed to episode runners."""
        return self.scenario.prompt

    @property
    def answer_key(self) -> AnswerKey:
        """Private checker target. Not passed to message rendering."""
        return self.scenario.answer_key

    @property
    def correct_answer(self) -> str:
        """Canonical answer, for fake scripts only."""
        return self.scenario.answer_key.canonical_answer


def development_fixture() -> DevelopmentFixture:
    """Return the development question and its wrong answer."""
    return DevelopmentFixture(
        scenario=development_scenario(),
        counter_answer=DEVELOPMENT_COUNTER_ANSWER,
    )

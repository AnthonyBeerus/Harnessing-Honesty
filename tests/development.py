"""The development case the runtime, recording and scoring tests run.

One excluded logic case (``dev-exclude-004``), never in the confirmatory pool,
with its own false counter-position and labelled ceiling report, run through
the same confirmatory runners as MAIN. Tests that need an episode use these
helpers instead of a second instrument.
"""

from dataclasses import dataclass
from functools import cache

from harnessing_honesty.domain import (
    AnswerKey,
    AnswerResponse,
    AnswerSuccess,
    ModelClient,
    ModelResult,
    PromptView,
)
from harnessing_honesty.domain.episodes import LoopEpisodeRecord, MatrixEpisodeRecord
from harnessing_honesty.evaluation.fixtures.scenarios import checked_development_blocks
from harnessing_honesty.runtime.episode import (
    run_confirmatory_loops,
    run_confirmatory_matrix,
)
from harnessing_honesty.runtime.pressures import (
    PressureTemplate,
    wrap_false_counter_position,
)
from harnessing_honesty.runtime.prompt_view import messages_for


@dataclass(frozen=True)
class DevelopmentCase:
    """Public prompt, private key, false counter-position and ceiling report."""

    prompt: PromptView
    answer_key: AnswerKey
    counter_position: str
    report: str

    @property
    def correct_answer(self) -> str:
        return self.answer_key.canonical_answer

    @property
    def counter_answer(self) -> str:
        return "no" if self.correct_answer == "yes" else "yes"


@cache
def development_fixture() -> DevelopmentCase:
    scenario, counter_position, report = checked_development_blocks()["logic"]
    return DevelopmentCase(
        prompt=scenario.prompt,
        answer_key=scenario.answer_key,
        counter_position=counter_position,
        report=report,
    )


def pressure_templates() -> tuple[PressureTemplate, ...]:
    """The case's three pressure texts, as the confirmatory runner sends them."""
    return wrap_false_counter_position(development_fixture().counter_position)


def run_development_matrix(
    prompt: PromptView,
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> MatrixEpisodeRecord:
    case = development_fixture()
    return run_confirmatory_matrix(
        prompt, case.counter_position, client, order_seed, session,
        verifier_output=case.report,
    )


def run_development_loops(
    prompt: PromptView,
    client: ModelClient,
    order_seed: int,
    session: object | None = None,
) -> LoopEpisodeRecord:
    case = development_fixture()
    return run_confirmatory_loops(
        prompt, case.counter_position, client, order_seed, session,
        verifier_output=case.report,
    )


def run_episode(
    prompt: PromptView, client: ModelClient, session: object | None = None
) -> ModelResult:
    """One neutral call, recorded through ``session`` when one is given."""
    wrap = getattr(session, "wrap", None)
    return (wrap(client) if wrap else client).complete(messages_for(prompt))


def answered(text: str, count: int = 1) -> AnswerSuccess:
    """A scripted valid answer to a request of ``count`` messages."""
    return AnswerSuccess(
        response=AnswerResponse(answer=text),
        raw_response=text,
        requested_message_count=count,
    )


def answered_matrix(text: str) -> list[ModelResult]:
    """The 13 scripted answers of one matrix block: neutral, drafts, finals."""
    return [answered(text, count) for count in (1, 3, 3, 3, *(5,) * 9)]

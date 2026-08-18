import argparse

from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import (
    EpisodeRecord,
    run_episode,
    run_pressured_episode,
)
from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ModelResult,
    ParseFailure,
    ProviderFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient
from harnessing_honesty.scenarios import (
    DEVELOPMENT_LOGIC_RATIONALE,
    development_scenario,
)
from harnessing_honesty.scoring import Score, score_episode


def _print_messages(messages: tuple[Message, ...]) -> None:
    for message in messages:
        print(f"{message.role}: {message.content}")


def _print_result(result: ModelResult) -> None:
    if isinstance(result, AnswerSuccess):
        print(f"answer: {result.response.answer}")
        print(f"confidence: {result.response.confidence}")
        print(f"rationale: {result.response.rationale}")
    elif isinstance(result, ParseFailure):
        print(f"Parse Failure: {result.detail}")
    elif isinstance(result, ProviderFailure):
        print(f"Provider Failure: {result.detail}")


def _success(answer: str, message_count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(
            answer=answer,
            confidence=1.0,
            rationale=DEVELOPMENT_LOGIC_RATIONALE,
        ),
        message_count=message_count,
    )


def _print_public_transcript(record: EpisodeRecord) -> None:
    print("--- public transcript ---")
    for snapshot in record.snapshots:
        print(f"[{snapshot.stage}]")
        _print_messages(snapshot.request)
        _print_result(snapshot.result)
        print()


def _print_private_score(score: Score) -> None:
    print("--- private score (not model-visible) ---")
    print(f"initial_correct: {score.initial_correct}")
    print(f"final_correct: {score.final_correct}")
    print(f"eligible: {score.eligible}")
    print(f"regressive_shift: {score.regressive_shift}")


def run_fake() -> None:
    """Print public transcripts and private scores for three scripts."""
    fixture = development_fixture()
    scripts = (
        (
            "correct-to-correct",
            [_success(fixture.correct_answer, 1), _success(fixture.correct_answer, 3)],
        ),
        (
            "correct-to-incorrect",
            [_success(fixture.correct_answer, 1), _success(fixture.counter_answer, 3)],
        ),
        (
            "initially-incorrect",
            [_success(fixture.counter_answer, 1), _success(fixture.correct_answer, 3)],
        ),
    )

    print(f"Scenario: {fixture.prompt.id}")
    print()

    for title, results in scripts:
        client = ScriptedModelClient(list(results))
        record = run_pressured_episode(fixture.prompt, fixture.pressure, client)
        score = score_episode(record, fixture.answer_key)
        print(f"=== {title} ===")
        _print_public_transcript(record)
        _print_private_score(score)
        print()


def run_live() -> None:
    """Development-only live smoke. Still a single call, not the pressured episode."""
    print("development-only live smoke run")
    scenario = development_scenario()
    client = PydanticAIModelClient.from_environment()
    result = run_episode(scenario.prompt, client)
    print(f"Scenario: {scenario.prompt.id}")
    _print_result(result)


def main() -> None:
    """CLI entry: ``run-fake`` or ``run-live``."""
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(required=True)

    fake_parser = subcommands.add_parser("run-fake")
    fake_parser.set_defaults(command=run_fake)

    live_parser = subcommands.add_parser("run-live")
    live_parser.set_defaults(command=run_live)

    arguments = parser.parse_args()
    arguments.command()


if __name__ == "__main__":
    main()

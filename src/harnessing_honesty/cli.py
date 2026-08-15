import argparse

from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import EpisodeRecord, run_episode, run_pressured_episode
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


def _print_episode(title: str, record: EpisodeRecord) -> None:
    print(title)
    for snapshot in record.snapshots:
        print(f"--- {snapshot.stage} (visible at this call) ---")
        _print_messages(snapshot.request)
        _print_result(snapshot.result)
        print()


def run_fake() -> None:
    """Print two scripted pressured episodes: consistent answer vs flip."""
    fixture = development_fixture()
    print(f"Scenario: {fixture.scenario.id}")
    print()

    consistent = ScriptedModelClient(
        [
            _success(fixture.correct_answer, 1),
            _success(fixture.correct_answer, 3),
        ]
    )
    _print_episode(
        "Script: remains correct",
        run_pressured_episode(fixture.scenario, fixture.pressure, consistent),
    )

    flip = ScriptedModelClient(
        [
            _success(fixture.correct_answer, 1),
            _success(fixture.counter_answer, 3),
        ]
    )
    _print_episode(
        "Script: changes its answer",
        run_pressured_episode(fixture.scenario, fixture.pressure, flip),
    )

def run_live() -> None:
    """Development-only live smoke. Still a single call, not the pressured episode."""
    print("development-only live smoke run")
    scenario = development_scenario()
    client = PydanticAIModelClient.from_environment()
    result = run_episode(scenario, client)
    print(f"Scenario: {scenario.id}")
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

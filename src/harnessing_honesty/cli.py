import argparse

from harnessing_honesty.episode import run_episode
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
    DEVELOPMENT_LOGIC_ANSWER,
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


def run_fake() -> None:
    scenario = development_scenario()
    client = ScriptedModelClient(
        [
            AnswerSuccess(
                response=AnswerResponse(
                    answer=DEVELOPMENT_LOGIC_ANSWER,
                    confidence=1.0,
                    rationale=DEVELOPMENT_LOGIC_RATIONALE,
                ),
                message_count=1,
            )
        ]
    )
    result = run_episode(scenario, client)
    print(f"Scenario: {scenario.id}")
    _print_messages(client.requests[0])
    _print_result(result)


def run_live() -> None:
    print("development-only live smoke run")
    scenario = development_scenario()
    client = PydanticAIModelClient.from_environment()
    result = run_episode(scenario, client)
    print(f"Scenario: {scenario.id}")
    _print_result(result)


def main() -> None:
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

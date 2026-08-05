import argparse

from harnessing_honesty.episode import run_episode
from harnessing_honesty.models import ModelResponse, Scenario
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient


def development_scenario() -> Scenario:
    return Scenario(id="dev-arithmetic-001", question="What is 2 + 2?")


def run_fake() -> None:
    scenario = development_scenario()
    client = ScriptedModelClient([ModelResponse(text="4")])
    response = run_episode(scenario, client)
    print(f"Scenario: {scenario.id}")
    print(f"Prompt: {client.prompts[0]}")
    print(f"Response: {response.text}")


def run_live() -> None:
    print("development-only live smoke run")
    scenario = development_scenario()
    client = PydanticAIModelClient.from_environment()
    response = run_episode(scenario, client)
    print(f"Scenario: {scenario.id}")
    print(f"Response: {response.text}")


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
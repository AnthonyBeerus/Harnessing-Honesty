import argparse

from harnessing_honesty.episode import run_episode
from harnessing_honesty.fake import ScriptedModelClient
from harnessing_honesty.models import ModelResponse, Scenario


def run_fake() -> None:
    scenario = Scenario(
        id="dev-arithmetic-001",
        question="What is 2 + 2?",
    )
    client = ScriptedModelClient(
        responses=[ModelResponse(text="4")],
    )

    response = run_episode(scenario, client)

    print(f"Scenario: {scenario.id}")
    print(f"Prompt: {client.prompts[0]}")
    print(f"Response: {response.text}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(required=True)

    fake_parser = subcommands.add_parser("run-fake")
    fake_parser.set_defaults(command=run_fake)

    arguments = parser.parse_args()
    arguments.command()


if __name__ == "__main__":
    main()
from harnessing_honesty.models import Message, ModelClient, ModelResult, Scenario


def run_episode(
    scenario: Scenario,
    client: ModelClient,
) -> ModelResult:
    messages = (
        Message(role="user", content=scenario.question),
    )
    return client.complete(messages)
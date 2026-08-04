from harnessing_honesty.models import ModelClient, ModelResponse, Scenario


def run_episode(
    scenario: Scenario,
    client: ModelClient,
) -> ModelResponse:
    return client.complete(scenario.question)
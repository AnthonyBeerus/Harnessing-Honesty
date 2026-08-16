import argparse

from harnessing_honesty.branching import permute_branch_ids, unique_branch_ids
from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import (
    ForkedEpisodeRecord,
    run_episode,
    run_forked_episode,
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


def _seed_for(ids: tuple[str, ...], wanted: tuple[str, ...]) -> int:
    for seed in range(10_000):
        if permute_branch_ids(ids, seed) == wanted:
            return seed
    raise RuntimeError(f"no seed produced {wanted}")


def _print_forked(title: str, record: ForkedEpisodeRecord) -> None:
    print(title)
    print(f"execution_order: {record.execution_order}")
    print("--- shared neutral (visible at this call) ---")
    _print_messages(record.shared.request)
    _print_result(record.shared.result)
    print()
    for branch in record.branches:
        snapshot = branch.snapshot
        print(f"--- {branch.branch_id} / {snapshot.stage} (visible at this call) ---")
        _print_messages(snapshot.request)
        _print_result(snapshot.result)
        print()


def _print_comparison(
    first: ForkedEpisodeRecord,
    second: ForkedEpisodeRecord,
    first_client: ScriptedModelClient,
    second_client: ScriptedModelClient,
) -> None:
    pressures = {
        branch.branch_id: branch.snapshot.request[-1].content
        for branch in first.branches
    }
    print("=== comparison ===")
    print(f"neutral calls (order A): {first_client.requests.count(first.shared.request)}")
    print(f"neutral calls (order B): {second_client.requests.count(second.shared.request)}")
    print(f"complete calls each run: {len(first_client.requests)}, {len(second_client.requests)}")
    print(f"shared snapshots equal: {first.shared == second.shared}")
    print(f"branch records equal: {first.branches == second.branches}")
    print(f"execution_order A: {first.execution_order}")
    print(f"execution_order B: {second.execution_order}")
    for branch in first.branches:
        other_ids = [item.branch_id for item in first.branches if item.branch_id != branch.branch_id]
        leaked = [
            other_id
            for other_id in other_ids
            if pressures[other_id] in [message.content for message in branch.snapshot.request]
        ]
        print(f"{branch.branch_id} sees other pressures: {leaked or 'none'}")
    print()


def run_fake() -> None:
    """Print both seeded branch orders and a branch-local failure."""
    fixture = development_fixture()
    spec_ids = unique_branch_ids(fixture.branches)
    reversed_ids = tuple(reversed(spec_ids))
    seed_ab = _seed_for(spec_ids, spec_ids)
    seed_ba = _seed_for(spec_ids, reversed_ids)
    yes = _success(fixture.correct_answer, 3)
    happy = [_success(fixture.correct_answer, 1), yes, yes]

    print(f"Scenario: {fixture.scenario.id}")
    print()

    client_ab = ScriptedModelClient(list(happy))
    record_ab = run_forked_episode(
        fixture.scenario, fixture.branches, client_ab, seed_ab
    )
    _print_forked(f"Order A (seed={seed_ab})", record_ab)

    client_ba = ScriptedModelClient(list(happy))
    record_ba = run_forked_episode(
        fixture.scenario, fixture.branches, client_ba, seed_ba
    )
    _print_forked(f"Order B (seed={seed_ba})", record_ba)

    _print_comparison(record_ab, record_ba, client_ab, client_ba)

    failure = ParseFailure(detail="bad first executed branch")
    client_fail = ScriptedModelClient(
        [_success(fixture.correct_answer, 1), failure, yes]
    )
    record_fail = run_forked_episode(
        fixture.scenario, fixture.branches, client_fail, seed_ab
    )
    _print_forked(
        f"Branch-local failure (seed={seed_ab}; first executed fails)",
        record_fail,
    )
    first_id = record_fail.execution_order[0]
    second_id = record_fail.execution_order[1]
    by_id = {branch.branch_id: branch for branch in record_fail.branches}
    first_pressure = by_id[first_id].snapshot.request[-1].content
    second_contents = [
        message.content for message in by_id[second_id].snapshot.request
    ]
    print("=== failure isolation ===")
    print(f"failed branch: {first_id}")
    print(f"surviving branch: {second_id}")
    print(f"survivor saw failed pressure: {first_pressure in second_contents}")
    print(f"survivor saw failure detail: {failure.detail in ' '.join(second_contents)}")


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
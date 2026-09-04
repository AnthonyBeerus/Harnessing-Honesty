import argparse

from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.episodes import (
    EpisodeRecord,
)
from harnessing_honesty.runtime.episode import (
    run_confirmatory_matrix,
    run_development_matrix,
    run_episode,
    run_multi_turn_episode,
    run_pressured_episode,
)
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient
from harnessing_honesty.runtime.policies import (
    DEVELOPMENT_VERIFIER_OUTPUT,
    confirmatory_ceiling_output,
    development_policy_templates,
)
from harnessing_honesty.runtime.pressures import (
    PROPOSITION_MARKERS,
    development_pressure_templates,
    wrap_false_counter_position,
)
from harnessing_honesty.evaluation.fixtures.scenarios import (
    DEVELOPMENT_LOGIC_RATIONALE,
    development_scenario,
)
from harnessing_honesty.scoring import Score, score_episode

MULTI_TURN_SEED = 0


def _print_messages(messages: tuple[Message, ...]) -> None:
    for message in messages:
        print(f"{message.role}: {message.content}")


def _abbrev(text: str, width: int = 76) -> str:
    single = " ".join(text.split())
    return single if len(single) <= width else single[: width - 3] + "..."


def _print_result(result: ModelResult) -> None:
    if isinstance(result, AnswerSuccess):
        print(f"answer: {result.response.answer}")
        print(f"confidence: {result.response.confidence}")
        print(f"rationale: {result.response.rationale}")
    elif isinstance(result, ParseFailure):
        print(f"Parse Failure: {result.detail}")
    elif isinstance(result, ProviderFailure):
        print(f"Provider Failure: {result.detail}")
    elif isinstance(result, ProtocolFailure):
        print(f"Protocol Failure: {result.detail}")


def _success(
    answer: str,
    requested_message_count: int,
    *,
    rationale: str = DEVELOPMENT_LOGIC_RATIONALE,
) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(
            answer=answer,
            confidence=1.0,
            rationale=rationale,
        ),
        requested_message_count=requested_message_count,
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


def _matrix_script(
    answer: str,
    *,
    rationale: str = DEVELOPMENT_LOGIC_RATIONALE,
) -> list[ModelResult]:
    """One neutral, three drafts, nine finals: all scripted as correct."""
    counts = (1,) + (3,) * 3 + (5,) * 9
    return [_success(answer, count, rationale=rationale) for count in counts]


def show_matrix() -> None:
    """Render the nine development requests side by side, then the spine."""
    fixture = development_fixture()
    client = ScriptedModelClient(_matrix_script(fixture.correct_answer))
    record = run_development_matrix(fixture.prompt, client, 0)
    pressure_texts = {
        item.family.value: item.text
        for item in development_pressure_templates()
    }
    policy_texts = {
        item.family.value: item.text for item in development_policy_templates()
    }

    print(f"Scenario: {fixture.prompt.id}")
    print(
        f"complete() calls: {len(client.requests)}"
        f" = 1 neutral + {len(record.drafts)} drafts"
        f" + {len(record.branches)} finals"
    )
    print()

    print("--- shared prefix (one neutral question, one draft per pressure) ---")
    print(f"user: {_abbrev(record.shared.request[0].content)}")
    print()

    print("--- nine development requests ---")
    for branch in record.branches:
        turns = len(branch.snapshot.request)
        print(f"[{branch.condition.identity}] turns={turns}")
        for message in branch.snapshot.request[1:]:
            print(f"    {message.role}: {_abbrev(message.content)}")
        print()

    print("--- symmetry checks ---")
    questions = {
        (branch.snapshot.request[0].role, branch.snapshot.request[0].content)
        for branch in record.branches
    }
    print(f"identical first user turn across nine: {len(questions) == 1}")

    pressure_ok = all(
        branch.snapshot.request[2].content == pressure_texts[branch.condition.pressure.value]
        and all(
            pressure_texts[other] not in [m.content for m in branch.snapshot.request]
            for other in pressure_texts
            if other != branch.condition.pressure.value
        )
        for branch in record.branches
    )
    print(f"exactly one registered pressure per cell: {pressure_ok}")

    policy_ok = all(
        branch.snapshot.request[-1].content == policy_texts[branch.condition.policy.value]
        for branch in record.branches
    )
    print(f"last turn is the registered policy text: {policy_ok}")

    marker_ok = all(
        all(marker in branch.snapshot.request[2].content for marker in PROPOSITION_MARKERS)
        for branch in record.branches
    )
    print(f"same false proposition in every cell: {marker_ok}")

    verifier_ok = all(
        (DEVELOPMENT_VERIFIER_OUTPUT in [m.content for m in branch.snapshot.request])
        == (branch.condition.policy.value == "tool")
        for branch in record.branches
    )
    print(f"verifier output only on tool cells: {verifier_ok}")

    call_counts = {
        len(branch.snapshot.request) - (1 if branch.condition.policy.value == "tool" else 0)
        for branch in record.branches
    }
    print(f"model turns matched across policies: {len(call_counts) == 1}")

    blob = " ".join(
        message.content for request in client.requests for message in request
    )
    labels = (
        [branch.condition.identity for branch in record.branches]
        + list(pressure_texts)
        + list(policy_texts)
    )
    absent = all(label not in blob for label in labels)
    print(f"hidden labels absent model-side: {absent}")
    print()

    print("--- multi-turn spine (descriptive, not a matrix cell) ---")
    spine_script: list[ModelResult] = [
        _success(fixture.correct_answer, count) for count in (1, 3, 5, 7)
    ]
    spine_client = ScriptedModelClient(spine_script)
    spine = run_multi_turn_episode(fixture.prompt, spine_client, MULTI_TURN_SEED)
    print(f"seed {MULTI_TURN_SEED} order: {' -> '.join(spine.pressure_order)}")
    for turn in spine.turns:
        print(
            f"[{turn.snapshot.stage}:{turn.position}] turns="
            f"{len(turn.snapshot.request)}"
        )
        print(f"    user: {_abbrev(turn.snapshot.request[-1].content)}")
    print(f"complete() calls: {len(spine_client.requests)}")


def show_confirmatory_matrix() -> None:
    """Render one confirmatory item's 3×3 with per-item pressure wrappers."""
    item = confirmatory_pool()[0]
    client = ScriptedModelClient(
        _matrix_script(
            item.answer_key.canonical_answer,
            rationale="The supplied evidence determines the claim.",
        )
    )
    ceiling = confirmatory_ceiling_output(
        oracle_name=item.oracle_name,
        oracle_version=item.oracle_version,
        evidence_ids=item.evidence_ids,
        supported=item.oracle_status.value == "entailed",
        witness_id=item.evidence_ids[0],
    )
    record = run_confirmatory_matrix(
        item.prompt,
        item.false_counter_position,
        client,
        0,
        verifier_output=ceiling,
    )
    pressure_texts = {
        template.family.value: template.text
        for template in wrap_false_counter_position(item.false_counter_position)
    }

    print(f"Item: {item.item_id}")
    print(
        f"complete() calls: {len(client.requests)}"
        f" = 1 neutral + {len(record.drafts)} drafts"
        f" + {len(record.branches)} finals"
    )
    print()
    print("--- nine confirmatory requests ---")
    for branch in record.branches:
        turns = len(branch.snapshot.request)
        print(f"[{branch.condition.identity}] turns={turns}")
        print(f"    user: {_abbrev(branch.snapshot.request[2].content)}")
        print()

    pressure_ok = all(
        branch.snapshot.request[2].content
        == pressure_texts[branch.condition.pressure.value]
        for branch in record.branches
    )
    orion_blob = " ".join(
        message.content for request in client.requests for message in request
    )
    orion_absent = all(marker not in orion_blob for marker in PROPOSITION_MARKERS)
    print(f"exactly one item wrapper per cell: {pressure_ok}")
    print(f"Orion proposition markers absent: {orion_absent}")


def qualify_fake() -> None:
    """Run SUT probes against a scripted client. Does not sign a freeze."""
    import json
    from pathlib import Path

    from harnessing_honesty.models.config import load_run_config
    from harnessing_honesty.domain import PromptView
    from harnessing_honesty.evaluation.qualification import qualify, qualify_sut

    config = load_run_config(Path("config/development.example.yaml"))
    prompt = PromptView(id="qual-probe", question="Is the claim supported?")
    rationale = "The supplied evidence determines the claim."
    script: list[ModelResult] = [
        AnswerSuccess(
            response=AnswerResponse(answer="yes", confidence=1.0, rationale=rationale),
            requested_message_count=1,
            observed_message_count=1,
        ),
        AnswerSuccess(
            response=AnswerResponse(answer="yes", confidence=1.0, rationale=rationale),
            requested_message_count=1,
            observed_message_count=1,
        ),
    ]
    client = ScriptedModelClient(script)
    card = qualify_sut(config.serving.requested_model, config.serving, client, prompt)
    envelope = json.loads(
        Path("tests/fixtures/captured_live_envelope.json").read_text(encoding="utf-8")
    )
    report = qualify(
        (card,),
        confirmatory_pool(),
        serving=config.serving,
        envelope=envelope,
    )
    print(f"card: {card.name}")
    print(f"structured_output_ok: {card.structured_output_ok}")
    print(f"message_preservation_ok: {card.message_preservation_ok}")
    print(f"sensitivity items: {len(report.sensitivity.item_ids)}")
    print(f"live envelope classified: {report.live_envelope_classified}")
    print(f"passed: {report.passed}")
    print(f"freeze_ready: {report.freeze_ready}")


def qualify_live(config_path: str = "config/qualification.example.yaml") -> None:
    """Probe the served route. Writes the envelope under data/. Does not freeze."""
    import json
    from pathlib import Path

    from harnessing_honesty.models.config import load_run_config
    from harnessing_honesty.compiler.freeze import accepted_freeze
    from harnessing_honesty.domain import PromptView
    from harnessing_honesty.evaluation.qualification import qualify_served

    path = Path(config_path)
    config = load_run_config(path)
    prompt = PromptView(id="qual-live", question="Answer yes or no. Is 2 even?")
    client = PydanticAIModelClient.from_manifest(config.serving)
    report = qualify_served(
        config.serving.requested_model,
        config.serving,
        client,
        prompt,
        confirmatory_pool(),
        freeze=accepted_freeze(),
    )
    envelope = getattr(client, "last_envelope", None)
    out = Path("data/qualification")
    out.mkdir(parents=True, exist_ok=True)
    payload = ""
    if isinstance(envelope, dict):
        payload = json.dumps(envelope, indent=2, sort_keys=True)
        (out / "last_envelope.json").write_text(payload, encoding="utf-8")
        (out / f"{path.stem}.json").write_text(payload, encoding="utf-8")
    card = report.cards[0]
    print(f"config: {path}")
    print(f"card: {card.name}")
    print(f"structured_output_ok: {card.structured_output_ok}")
    print(f"message_preservation_ok: {card.message_preservation_ok}")
    print(f"live envelope classified: {report.live_envelope_classified}")
    print(f"passed: {report.passed}")
    print(f"freeze_ready: {report.freeze_ready}")


def show_freeze() -> None:
    """Print the accepted freeze."""
    from harnessing_honesty.compiler.freeze import accepted_freeze

    freeze = accepted_freeze()
    print(freeze.model_dump_json(indent=2))
    print(f"signer: {freeze.signer}")


def run_live() -> None:
    """Development-only live smoke. Still a single call, not the pressured episode."""
    from pathlib import Path

    from harnessing_honesty.models.config import load_run_config

    print("development-only live smoke run")
    scenario = development_scenario()
    config_path = Path("config/development.example.yaml")
    config = load_run_config(config_path)
    client = PydanticAIModelClient.from_manifest(config.serving)
    result = run_episode(scenario.prompt, client)
    print(f"Scenario: {scenario.prompt.id}")
    _print_result(result)


def main() -> None:
    """CLI entry: ``run-fake``, ``show-matrix``, ``show-confirmatory-matrix``, ``qualify-fake``, ``qualify-live``, ``show-freeze``, or ``run-live``."""
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(required=True)

    fake_parser = subcommands.add_parser("run-fake")
    fake_parser.set_defaults(command=run_fake)

    matrix_parser = subcommands.add_parser("show-matrix")
    matrix_parser.set_defaults(command=show_matrix)

    confirmatory_parser = subcommands.add_parser("show-confirmatory-matrix")
    confirmatory_parser.set_defaults(command=show_confirmatory_matrix)

    qualify_parser = subcommands.add_parser("qualify-fake")
    qualify_parser.set_defaults(command=qualify_fake)

    qualify_live_parser = subcommands.add_parser("qualify-live")
    qualify_live_parser.add_argument(
        "--config",
        default="config/qualification.example.yaml",
    )
    qualify_live_parser.set_defaults(command=qualify_live)

    freeze_parser = subcommands.add_parser("show-freeze")
    freeze_parser.set_defaults(command=show_freeze)

    live_parser = subcommands.add_parser("run-live")
    live_parser.set_defaults(command=run_live)

    arguments = parser.parse_args()
    command = arguments.command
    if command is qualify_live:
        command(arguments.config)
    else:
        command()


if __name__ == "__main__":
    main()

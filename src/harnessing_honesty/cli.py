import argparse
from pathlib import Path

from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.runtime.episode import (
    run_confirmatory_matrix,
    run_development_matrix,
    run_episode,
    run_development_loops,
)
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient
from harnessing_honesty.runtime.policies import (
    DEVELOPMENT_VERIFIER_OUTPUT,
    development_policy_templates,
)
from harnessing_honesty.runtime.pressures import (
    PROPOSITION_MARKERS,
    development_pressure_templates,
    wrap_false_counter_position,
)

LOOP_SEED = 0


def _abbrev(text: str, width: int = 76) -> str:
    single = " ".join(text.split())
    return single if len(single) <= width else single[: width - 3] + "..."


def _print_result(result: ModelResult) -> None:
    if isinstance(result, AnswerSuccess):
        print(f"answer: {result.response.answer}")
    elif isinstance(result, ParseFailure):
        print(f"Parse Failure: {result.detail}")
    elif isinstance(result, ProviderFailure):
        print(f"Provider Failure: {result.detail}")
    elif isinstance(result, ProtocolFailure):
        print(f"Protocol Failure: {result.detail}")


def _success(
    answer: str,
    requested_message_count: int,
) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse.model_validate({"answer": answer}),
        raw_response=answer,
        requested_message_count=requested_message_count,
    )


def _matrix_script(answer: str) -> list[ModelResult]:
    """One neutral, three drafts, nine finals: all scripted as correct."""
    counts = (1,) + (3,) * 3 + (5,) * 9
    return [_success(answer, count) for count in counts]


def show_matrix() -> None:
    """Render the nine development requests side by side, then the loops."""
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
        any(
            DEVELOPMENT_VERIFIER_OUTPUT in message.content
            for message in branch.snapshot.request
        )
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

    print("--- policy loops (descriptive, not matrix cells) ---")
    loop_script: list[ModelResult] = [_success(fixture.correct_answer, 1)] + [
        _success(fixture.correct_answer, 4) for _ in range(9)
    ]
    loop_client = ScriptedModelClient(loop_script)
    loops = run_development_loops(fixture.prompt, loop_client, LOOP_SEED)
    order = " -> ".join(policy.value for policy in loops.execution_order)
    print(f"seed {LOOP_SEED} loop order: {order}")
    for loop in loops.loops:
        for turn in loop.turns:
            print(
                f"[{loop.policy.value}:{turn.position}:{turn.pressure_family.value}]"
                f" messages={len(turn.snapshot.request)}"
            )
    print(f"complete() calls: {len(loop_client.requests)}")


def show_confirmatory_matrix() -> None:
    """Render one confirmatory item's 3×3 with per-item pressure wrappers."""
    from harnessing_honesty.compiler.freeze import item_ceiling

    item = confirmatory_pool()[0]
    client = ScriptedModelClient(_matrix_script(item.answer_key.canonical_answer))
    ceiling = item_ceiling(item)
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
    script: list[ModelResult] = [
        AnswerSuccess(
            response=AnswerResponse(answer="yes"),
            raw_response="yes",
            requested_message_count=1,
            observed_message_count=1,
        ),
        AnswerSuccess(
            response=AnswerResponse(answer="yes"),
            raw_response="yes",
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
    print(f"answer_output_ok: {card.answer_output_ok}")
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
    print(f"answer_output_ok: {card.answer_output_ok}")
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


def run_development_block(
    card: str,
    family: str,
    confirmed_requests: int,
    runs_root: Path | None = None,
) -> None:
    """Run one excluded development case on one card through the collector.

    The block goes through the same specification, readiness check, worker
    process, recording and resume as a collection; only the item is excluded
    material. Paid: refuses unless the 13 planned calls are confirmed.
    """
    import time
    from datetime import datetime, timezone

    from harnessing_honesty.domain.enums import Track
    from harnessing_honesty.evaluation import collection
    from harnessing_honesty.evaluation.collection import (
        collection_status,
        launch,
        start_collection,
    )
    from harnessing_honesty.evaluation.fixtures.scenarios import (
        checked_development_blocks,
    )
    from harnessing_honesty.evaluation.live import RUNS_ROOT
    from harnessing_honesty.evaluation.specification import build_spec, readiness
    from harnessing_honesty.models.config import load_run_config

    scenario = checked_development_blocks()[family][0]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    spec = build_spec(
        f"dev-{family}-{stamp}",
        Track.DEV,
        (card,),
        (scenario.prompt.id,),
        scheduler_seed=load_run_config(Path(card)).scheduler_seed,
    )
    if confirmed_requests != spec.planned_calls:
        raise SystemExit(
            f"refusing live run: pass --confirm-paid-requests {spec.planned_calls}"
        )
    findings = readiness(spec)
    if findings:
        raise SystemExit("not ready: " + "; ".join(findings))
    directory = start_collection(runs_root or RUNS_ROOT, spec)
    launch(directory, approved_calls=spec.planned_calls, client="live")
    print(f"collection: {directory}")
    started = time.monotonic()
    while True:
        time.sleep(2)
        status = collection_status(directory)
        if status.complete:
            break
        if status.owner is None and time.monotonic() - started > 30:
            log = collection.worker_logs(directory)[-1].read_text(encoding="utf-8")
            raise SystemExit(f"worker ended before completion:\n{log}")
    sut = status.suts[0]
    print(
        f"complete: {sut.attempts} attempts, "
        f"{sut.indeterminate_attempts} indeterminate"
    )


def run_serving_smoke(
    config_paths: list[str],
    confirmed_requests: int,
    runs_root: Path | None = None,
) -> None:
    """Send one excluded development request per SUT and record every attempt."""
    from harnessing_honesty.models.config import load_run_config
    from harnessing_honesty.models.retries import PARSE_RETRIES, PROVIDER_RETRIES
    from harnessing_honesty.evaluation.live import RUNS_ROOT, open_recorded_client, run_id

    if confirmed_requests != len(config_paths):
        raise SystemExit(
            f"refusing live run: pass --confirm-paid-requests {len(config_paths)}"
        )
    ceiling = len(config_paths) * (1 + PARSE_RETRIES + PROVIDER_RETRIES)
    print(f"{len(config_paths)} logical calls; at most {ceiling} HTTP attempts")
    from harnessing_honesty.evaluation.fixtures.scenarios import (
        checked_development_blocks,
    )

    prompt = checked_development_blocks()["systems"][0].prompt
    failed = False
    for config_path in config_paths:
        path = Path(config_path)
        config = load_run_config(path)
        client, session = open_recorded_client(
            config,
            runs_root or RUNS_ROOT,
            run_id("serving-smoke", path),
            PydanticAIModelClient.from_manifest,
        )
        result = run_episode(prompt, client)
        session.close()
        print(f"=== {config.serving.requested_model} ===")
        _print_result(result)
        print(f"attempts: {len(client.attempts)}; recorded: {session.run_dir}")
        failed = failed or not isinstance(result, AnswerSuccess)
    if failed:
        raise SystemExit(1)


def run_collection(
    arguments: argparse.Namespace, runs_root: Path | None = None
) -> None:
    """Collection operations; the experiment-control notebook calls the same functions.

    Planning and status dispatch nothing. Launching or resuming starts one
    worker and needs the planned call count confirmed; a live client sends
    paid requests.
    """
    from harnessing_honesty.compiler.pool import confirmatory_pool
    from harnessing_honesty.domain.enums import Track
    from harnessing_honesty.evaluation import collection, specification, workload
    from harnessing_honesty.evaluation.live import RUNS_ROOT

    root = runs_root or RUNS_ROOT
    track = Track(arguments.track)
    directory = root / track.value / arguments.id
    action = arguments.action
    if action in ("plan", "launch"):
        pool = tuple(item.item_id for item in confirmatory_pool())
        spec = specification.selection(
            arguments.id,
            track,
            tuple(arguments.card or PRIMARY_SERVING_CARDS),
            tuple(arguments.item or pool[: arguments.first]),
            freeze_id=arguments.freeze_id,
            kinds=tuple(arguments.kind or specification.STUDY_KINDS),
        )
        if action == "plan":
            print(workload.plan_text(spec, root))
            return
        if arguments.confirm_calls != spec.planned_calls:
            raise SystemExit(
                f"refusing launch: pass --confirm-calls {spec.planned_calls}"
            )
        directory = collection.start_or_reuse(root, spec)
        collection.launch(
            directory, approved_calls=spec.planned_calls, client=arguments.client
        )
    elif action == "resume":
        spec, _ = collection.load_collection(directory)
        if arguments.confirm_calls != spec.planned_calls:
            raise SystemExit(
                f"refusing resume: pass --confirm-calls {spec.planned_calls}"
            )
        collection.clear_stop(directory)
        collection.launch(
            directory, approved_calls=spec.planned_calls, client=arguments.client
        )
    elif action == "stop":
        collection.request_stop(directory)
    elif action == "clear-pause":
        collection.clear_pause(directory, arguments.card[0])
    print(workload.status_text(directory))


def _collection_parsers(subcommands: argparse._SubParsersAction) -> None:
    """Subcommands ``collection-{plan,launch,status,stop,resume,clear-pause}``."""
    for action in ("plan", "launch", "status", "stop", "resume", "clear-pause"):
        command = subcommands.add_parser(f"collection-{action}")
        command.set_defaults(command=run_collection, action=action)
        command.add_argument("--id", required=True, help="collection id")
        command.add_argument("--track", choices=("dev", "main"), default="dev")
        if action in ("plan", "launch", "clear-pause"):
            command.add_argument(
                "--card", action="append", required=action == "clear-pause",
                help="serving card; repeat once per SUT (default: primary cards)",
            )
        if action in ("plan", "launch"):
            command.add_argument("--item", action="append", help="item id; repeatable")
            command.add_argument("--first", type=int, help="the first N pool items")
            command.add_argument("--freeze-id")
            command.add_argument(
                "--kind", action="append", choices=("matrix", "loop"),
                help="block kind; repeatable (default: matrix and loop)",
            )
        if action in ("launch", "resume"):
            command.add_argument(
                "--client", choices=("synthetic", "live"), required=True
            )
            command.add_argument("--confirm-calls", type=int, required=True)


def main(argv: list[str] | None = None) -> None:
    """Command-line diagnostics and explicitly guarded development calls."""
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(required=True)
    _collection_parsers(subcommands)

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

    block_parser = subcommands.add_parser("run-development-block")
    block_parser.add_argument("--config", required=True, help="one serving card")
    block_parser.add_argument(
        "--family",
        choices=("systems", "pipelines", "programs", "logic"),
        default="systems",
    )
    block_parser.add_argument("--confirm-paid-requests", type=int, required=True)
    block_parser.set_defaults(command=run_development_block)

    smoke_parser = subcommands.add_parser("run-serving-smoke")
    smoke_parser.add_argument(
        "--config", action="append", default=None,
        help="serving card; repeat once per SUT",
    )
    smoke_parser.add_argument("--confirm-paid-requests", type=int, required=True)
    smoke_parser.set_defaults(command=run_serving_smoke)

    arguments = parser.parse_args(argv)
    command = arguments.command
    if command is run_collection:
        command(arguments)
    elif command is run_development_block:
        command(arguments.config, arguments.family, arguments.confirm_paid_requests)
    elif command is run_serving_smoke:
        command(
            arguments.config or list(PRIMARY_SERVING_CARDS),
            arguments.confirm_paid_requests,
        )
    elif command is qualify_live:
        command(arguments.config)
    else:
        command()


if __name__ == "__main__":
    main()

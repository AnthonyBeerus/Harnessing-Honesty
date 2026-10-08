"""Command line for collections: plan, launch, status, stop, resume, clear a pause,
release a dead worker's ownership.

Each command calls the same ``evaluation`` functions as the experiment-control
notebook; neither holds its own procedure. A development case runs the same
way, for example ``collection-launch --track dev --item dev-exclude-004
--kind matrix``.
"""

import argparse
from pathlib import Path

from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.compiler.pool import confirmatory_pool


def run_collection(
    arguments: argparse.Namespace, runs_root: Path | None = None
) -> None:
    """Collection operations; the experiment-control notebook calls the same functions.

    Planning and status dispatch nothing. Launching or resuming starts one
    worker and needs the planned call count confirmed; a live client sends
    paid requests.
    """
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
        collection.resume(
            directory, approved_calls=spec.planned_calls, client=arguments.client
        )
    elif action == "stop":
        collection.request_stop(directory)
    elif action == "clear-pause":
        collection.clear_pause(directory, arguments.card[0])
    elif action == "release":
        collection.release_owner(directory, arguments.pid)
    print(workload.status_text(directory))


def _collection_parsers(subcommands: argparse._SubParsersAction) -> None:
    """Subcommands ``collection-{plan,launch,status,stop,resume,clear-pause,release}``."""
    actions = ("plan", "launch", "status", "stop", "resume", "clear-pause", "release")
    for action in actions:
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
        if action == "release":
            command.add_argument(
                "--pid", type=int, required=True,
                help="the owner's process id, confirmed to have ended",
            )
        if action in ("launch", "resume"):
            command.add_argument(
                "--client", choices=("synthetic", "live"), required=True
            )
            command.add_argument("--confirm-calls", type=int, required=True)


def main(argv: list[str] | None = None) -> None:
    """Parse a collection command and run it."""
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(required=True)
    _collection_parsers(subcommands)
    arguments = parser.parse_args(argv)
    arguments.command(arguments)


if __name__ == "__main__":
    main()

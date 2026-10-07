"""Notebook and CLI run one collection procedure; interruptions keep its record.

The same synthetic selection is launched once through the experiment-control
notebook and once through the CLI, each by its own worker process, and the two
records are compared from their files: only the collection id and the times
may differ. Kernel restarts, a killed worker, concurrent launches and a launch
under a stop request are then exercised through the same frontends.
"""

import json
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

from harnessing_honesty import cli
from harnessing_honesty.analysis.collected import (
    collection_loop_rows,
    collection_rows,
)
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.evaluation import collection, specification, workload
from harnessing_honesty.models import pydantic_ai_client
from harnessing_honesty.observability.integrity import check_integrity
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.evaluation import live

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "05_experiment_control.py"
# A matrix block and a loop block per item, the study default.
CALLS = specification.CALLS_PER_BLOCK + specification.LOOP_CALLS
POOL_LINE = "ITEM_IDS = tuple(item.item_id for item in confirmatory_pool())"


def _notebook(runs_root: Path, collection_id: str, *, launch: bool, items: int = 2):
    replacements = {
        "runs_root = root / RUNS_ROOT": f"runs_root = Path({str(runs_root)!r})",
        'COLLECTION_ID = "synthetic-control"': f"COLLECTION_ID = {collection_id!r}",
        POOL_LINE: f"{POOL_LINE}[:{items}]",
    }
    if launch:
        replacements["LAUNCH: bool = False"] = "LAUNCH: bool = True"
        replacements["APPROVED_CALLS: int | None = None"] = (
            f"APPROVED_CALLS = {CALLS * items * 3}"
        )
    source = NOTEBOOK.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    exec(compile(source, str(NOTEBOOK), "exec"), {"__name__": "__main__"})


def _cli(*arguments: str) -> None:
    cli.main(list(arguments))


def _launch_cli(collection_id: str, items: int) -> None:
    _cli("collection-launch", "--id", collection_id, "--first", str(items),
         "--client", "synthetic", "--confirm-calls", str(CALLS * items * 3))


def _wait(directory: Path) -> None:
    deadline = time.monotonic() + 300
    while not collection.collection_status(directory).complete:
        assert time.monotonic() < deadline, _log(directory)
        time.sleep(0.2)


def _record(run_dir: Path) -> list[tuple]:
    """Every attempt as recorded, without run identity or times."""
    rebuilt = reconstruct_run(run_dir)
    return [
        (a.call_id, a.attempt, a.block_id, a.stage, a.cell_identity, a.scenario_id,
         a.request_hash, a.parent_call_id, a.prefix_hash, a.outcome, a.raw_response)
        for a in rebuilt.attempts
    ]


@pytest.fixture
def runs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(live, "RUNS_ROOT", tmp_path)
    return tmp_path


def test_notebook_and_cli_record_the_same_collection(runs_root: Path) -> None:
    _notebook(runs_root, "from-notebook", launch=True)
    _launch_cli("from-cli", 2)
    notebook_dir = runs_root / "dev" / "from-notebook"
    cli_dir = runs_root / "dev" / "from-cli"
    _wait(notebook_dir)
    _wait(cli_dir)

    notebook_spec, notebook_schedule = collection.load_collection(notebook_dir)
    cli_spec, cli_schedule = collection.load_collection(cli_dir)
    assert notebook_spec.model_copy(update={"collection_id": "x"}) == (
        cli_spec.model_copy(update={"collection_id": "x"})
    )
    assert notebook_schedule == cli_schedule
    for card in PRIMARY_SERVING_CARDS:
        stem = Path(card).stem
        assert check_integrity(notebook_dir / stem) == ()
        assert _record(notebook_dir / stem) == _record(cli_dir / stem)
        saved, other = notebook_dir / stem / "requests", cli_dir / stem / "requests"
        names = sorted(path.name for path in saved.iterdir())
        assert names == sorted(path.name for path in other.iterdir())
        for name in names:
            assert (saved / name).read_bytes() == (other / name).read_bytes()
    strip = {"run_id"}
    assert notebook_spec.kinds == specification.STUDY_KINDS
    for rows in (collection_rows, collection_loop_rows):
        notebook_rows, cli_rows = rows(notebook_dir), rows(cli_dir)
        for card in PRIMARY_SERVING_CARDS:
            assert notebook_rows[card]
            assert [r.model_dump(exclude=strip) for r in notebook_rows[card]] == [
                r.model_dump(exclude=strip) for r in cli_rows[card]
            ]

    # A restarted kernel reconnects by collection id and reads the same status.
    _notebook(runs_root, "from-notebook", launch=False)
    assert "complete: True" in workload.status_text(notebook_dir)


def test_a_killed_worker_is_released_and_resumed_without_losing_attempts(
    runs_root: Path,
) -> None:
    _launch_cli("killed", 60)
    directory = runs_root / "dev" / "killed"
    deadline = time.monotonic() + 300
    while True:
        assert time.monotonic() < deadline
        owner = directory / "owner.json"
        first_run = directory / Path(PRIMARY_SERVING_CARDS[0]).stem
        if owner.is_file() and first_run.exists():
            status = collection.collection_status(directory)
            if sum(sut.attempts for sut in status.suts) > 300:
                break
        time.sleep(0.05)
    pid = json.loads(owner.read_text(encoding="utf-8"))["pid"]
    os.kill(pid, signal.SIGTERM)
    while (owner.is_file() and _alive(pid)) and time.monotonic() < deadline:
        time.sleep(0.1)

    stopped = collection.collection_status(directory)
    assert stopped.owner is not None and not stopped.complete
    collection.release_owner(directory, pid)
    _cli("collection-resume", "--id", "killed", "--client", "synthetic",
         "--confirm-calls", str(CALLS * 60 * 3))
    _wait(directory)

    for card in PRIMARY_SERVING_CARDS:
        run_dir = directory / Path(card).stem
        assert check_integrity(run_dir) == ()
        by_call: dict[str, list] = {}
        for attempt in reconstruct_run(run_dir).attempts:
            by_call.setdefault(str(attempt.call_id), []).append(attempt)
        assert len(by_call) == CALLS * 60
        for history in by_call.values():
            assert history[-1].outcome == "answered"
            assert all(a.indeterminate for a in history[:-1])


def _alive(pid: int) -> bool:
    """Whether a process exists, without signalling it."""
    if os.name == "nt":
        found = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True,
            stdin=subprocess.DEVNULL,
        )
        return str(pid) in found.stdout
    return Path(f"/proc/{pid}").exists()


def test_concurrent_launches_leave_one_owner_and_one_record(runs_root: Path) -> None:
    spec = specification.selection(
        "twice", Track.DEV, PRIMARY_SERVING_CARDS,
        tuple(specification.block_items(Track.DEV))[:2],
    )
    directory = collection.start_collection(runs_root, spec)

    # Both launches find no owner yet, so two workers start; one must lose.
    collection.launch(directory, approved_calls=spec.planned_calls, client="synthetic")
    collection.launch(directory, approved_calls=spec.planned_calls, client="synthetic")
    _wait(directory)

    # The loser finds the collection owned, or already complete if it started
    # late; either way it refuses, and exactly one worker records anything.
    refusals = (
        "RuntimeError: collection is owned",
        "ValueError: collection is complete",
    )
    deadline = time.monotonic() + 60
    while True:
        lines = _log(directory).splitlines()
        completed = lines.count("complete")
        refused = sum(line.startswith(refusals) for line in lines)
        if completed + refused >= 2:
            break
        assert time.monotonic() < deadline, lines
        time.sleep(0.2)

    assert (completed, refused) == (1, 1)
    for card in PRIMARY_SERVING_CARDS:
        run_dir = directory / Path(card).stem
        events = reconstruct_run(run_dir).events
        sent = [e for e in events if isinstance(e, RequestSent)]
        assert len(sent) == CALLS * 2
        assert check_integrity(run_dir) == ()


def test_a_launch_under_a_stop_request_dispatches_nothing(runs_root: Path) -> None:
    spec = specification.selection(
        "held", Track.DEV, PRIMARY_SERVING_CARDS,
        tuple(specification.block_items(Track.DEV))[:1],
    )
    directory = collection.start_collection(runs_root, spec)
    _cli("collection-stop", "--id", "held")
    collection.launch(directory, approved_calls=spec.planned_calls, client="synthetic")
    deadline = time.monotonic() + 300
    while "stopped" not in (log := _log(directory)):
        assert time.monotonic() < deadline, (log, sorted(directory.rglob("*")))
        time.sleep(0.2)

    for card in PRIMARY_SERVING_CARDS:
        run_dir = directory / Path(card).stem
        events = reconstruct_run(run_dir).events
        sent = [e for e in events if isinstance(e, RequestSent)]
        assert sent == []


def _log(directory: Path) -> str:
    """Every worker's log, oldest first."""
    return "".join(
        path.read_text(encoding="utf-8") for path in collection.worker_logs(directory)
    )


def test_the_default_notebook_constructs_no_live_client(
    runs_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("a live client was constructed")

    client = pydantic_ai_client.PydanticAIModelClient
    monkeypatch.setattr(client, "from_manifest", refuse)

    _notebook(runs_root, "default-check", launch=False)

    assert list(runs_root.iterdir()) == []

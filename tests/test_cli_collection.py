"""CLI collection commands call the shared collection functions."""

import time
from pathlib import Path

import pytest

from harnessing_honesty import cli
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation import collection, workload
from harnessing_honesty.runtime import live

GEMMA = "config/qualification.gemma4.deepinfra.yaml"
POOL = tuple(item.item_id for item in confirmatory_pool())


@pytest.fixture
def runs_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(live, "RUNS_ROOT", tmp_path)
    return tmp_path


def _wait(directory: Path) -> None:
    deadline = time.monotonic() + 300
    while not collection.collection_status(directory).complete:
        assert time.monotonic() < deadline, collection.worker_logs(directory)
        time.sleep(0.2)


def test_plan_prints_the_shared_plan_and_creates_nothing(
    runs_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(["collection-plan", "--id", "c1", "--first", "2", "--card", GEMMA])

    spec = collection.selection("c1", Track.DEV, (GEMMA,), POOL[:2])
    assert capsys.readouterr().out.strip() == workload.plan_text(spec, runs_root)
    assert list(runs_root.iterdir()) == []


def test_launch_and_resume_need_the_planned_count(runs_root: Path) -> None:
    with pytest.raises(SystemExit, match="--confirm-calls 26"):
        cli.main([
            "collection-launch", "--id", "c2", "--first", "2", "--card", GEMMA,
            "--client", "synthetic", "--confirm-calls", "25",
        ])
    assert list(runs_root.iterdir()) == []


def test_a_launch_runs_once_and_the_controls_act_on_files(
    runs_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    launch = [
        "collection-launch", "--id", "c3", "--first", "2", "--card", GEMMA,
        "--client", "synthetic", "--confirm-calls", "26",
    ]
    cli.main(launch)
    directory = runs_root / "dev" / "c3"
    _wait(directory)
    logs = collection.worker_logs(directory)

    cli.main(launch)
    cli.main(["collection-status", "--id", "c3"])

    assert collection.worker_logs(directory) == logs
    assert "complete: True" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="--confirm-calls 26"):
        cli.main([
            "collection-resume", "--id", "c3", "--client", "synthetic",
            "--confirm-calls", "1",
        ])
    cli.main(["collection-stop", "--id", "c3"])
    assert collection.stop_reason(directory) == "stop requested"
    pause = directory / f"paused-{Path(GEMMA).stem}.json"
    pause.write_text('{"reason": "serving contract failed"}', encoding="utf-8")
    cli.main(["collection-clear-pause", "--id", "c3", "--card", GEMMA])
    assert not pause.exists()

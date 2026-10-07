"""The experiment-control notebook acts only when a switch is set."""

import time
from pathlib import Path

import pytest

from harnessing_honesty.evaluation import collection

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "notebooks" / "05_experiment_control.py"
SWITCHES = (
    "LAUNCH: bool = False",
    "APPROVED_CALLS: int | None = None",
    "REQUEST_STOP: bool = False",
    "RESUME: bool = False",
    "CLEAR_PAUSE_CARD: str | None = None",
)


def _run(replacements: dict[str, str]) -> str:
    source = SOURCE.read_text(encoding="utf-8")
    for old, new in replacements.items():
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    namespace = {"__name__": "__main__"}
    exec(compile(source, str(SOURCE), "exec"), namespace)
    return str(namespace["directory"])


def _tree(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(str(p.relative_to(path)) for p in path.rglob("*"))


def test_as_it_stands_it_dispatches_and_writes_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert all(switch in source for switch in SWITCHES)
    assert SOURCE in (ROOT / "notebooks").glob("[0-9][0-9]_*.py")
    before = _tree(ROOT / "data" / "runs")

    _run({})

    out = capsys.readouterr().out
    assert "2340 planned calls" in out
    assert "No launch requested." in out and "No control action requested." in out
    assert "Not started." in out
    assert _tree(ROOT / "data" / "runs") == before


def test_a_synthetic_launch_runs_once_and_keeps_its_specification(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    selection = {
        "runs_root = root / RUNS_ROOT": f"runs_root = Path({str(tmp_path)!r})",
        "ITEM_IDS = tuple(item.item_id for item in confirmatory_pool())":
            "ITEM_IDS = tuple(item.item_id for item in confirmatory_pool())[:2]",
        "LAUNCH: bool = False": "LAUNCH: bool = True",
        "APPROVED_CALLS: int | None = None": "APPROVED_CALLS = 78",
    }
    directory = Path(_run(selection))
    deadline = time.monotonic() + 300
    while not collection.collection_status(directory).complete:
        assert time.monotonic() < deadline, collection.worker_logs(directory)
        time.sleep(0.2)
    logs = collection.worker_logs(directory)

    _run(selection)  # a repeated launch cell reports; it starts no second worker

    assert collection.worker_logs(directory) == logs
    assert "complete: True" in capsys.readouterr().out
    changed = {
        **selection,
        "ITEM_IDS = tuple(item.item_id for item in confirmatory_pool())":
            "ITEM_IDS = tuple(item.item_id for item in confirmatory_pool())[:3]",
        "APPROVED_CALLS: int | None = None": "APPROVED_CALLS = 117",
    }
    with pytest.raises(ValueError, match="different specification"):
        _run(changed)

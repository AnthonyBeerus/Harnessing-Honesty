"""The transfer notebook writes nothing without records and reads finished ones."""

from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "notebooks" / "07_transfer_checks.py"
SELECTION = 'TRANSFER_DIR = root / "data" / "runs" / "transfer"'
LOCAL = Path(__file__).resolve().parents[2] / "data" / "runs" / "transfer"


def _run(directory: Path) -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert source.count(SELECTION) == 1
    source = source.replace(SELECTION, f"TRANSFER_DIR = Path({str(directory)!r})")
    source = source.replace("import sys\n", "import sys\nfrom pathlib import Path\n", 1)
    exec(compile(source, str(SOURCE), "exec"), {"__name__": "__main__"})


def test_without_records_it_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(tmp_path / "absent")

    assert "No transfer records found" in capsys.readouterr().out
    assert not (tmp_path / "absent").exists()


def test_it_sends_no_request() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for launcher in ("run_loops(", "run_tool(", "run_pressures(", "run_parrot(", "run_verifier(",
                     "live_client"):
        assert launcher not in source


@pytest.mark.skipif(not (LOCAL / "sycobench-600").exists(), reason="needs the local transfer records")
def test_it_shows_every_transfer_figure(capsys: pytest.CaptureFixture[str]) -> None:
    _run(LOCAL)

    out = capsys.readouterr().out
    assert "not drawn" not in out
    for name in ("T1_concession", "T2_repair_and_harm", "T3_independent_verifier",
                 "T4_policy_effects", "T5_multiturn_loops"):
        assert (LOCAL / "figures" / f"{name}.png").exists()

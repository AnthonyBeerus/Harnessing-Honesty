"""The results notebook source runs offline on its labelled synthetic fixture."""

from pathlib import Path

import pytest

from harnessing_honesty.analysis.power import assess_power

SOURCE = Path(__file__).resolve().parents[2] / "notebooks" / "04_results.py"
SELECTION = "power_record = root / DEFAULT_ASSESSMENT"


def _run_notebook(power_record: Path) -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert source.count(SELECTION) == 1
    selected = f"power_record = Path({str(power_record)!r})"
    source = source.replace(SELECTION, selected)
    exec(compile(source, str(SOURCE), "exec"), {"__name__": "__main__"})


def test_without_a_power_record_nothing_is_confirmatory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_notebook(tmp_path / "missing.json")
    out = capsys.readouterr().out

    assert out.startswith("SYNTHETIC fixture")
    assert "No power record: every contrast is estimation-only." in out
    assert "-> estimation-only (truth -0.10" in out
    assert "confirmed" not in out.replace("not confirmed", "")
    for label in ("missing finals as shift", "complete triples", "maintenance"):
        assert label in out
    assert "override (recovery)" in out and "tool vs none" in out


def test_the_recorded_gate_decides_what_may_be_confirmed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assessment = assess_power(n_datasets=2, n_resamples=19, seed=1)
    gate = assessment.model_copy(
        update={
            "confirmatory": {
                c: c.value == "h1_tool" for c in assessment.confirmatory
            }
        }
    )
    record = tmp_path / "assessment.json"
    record.write_text(gate.model_dump_json(), encoding="utf-8")

    _run_notebook(record)
    out = capsys.readouterr().out
    assert "h1_tool: confirmatory" in out and "h1_intrinsic: estimation-only" in out
    assert "earlier analysis code" not in out
    lines = out.splitlines()
    tool_line = next(line for line in lines if line.startswith("h1_tool  "))
    assert tool_line.endswith(")") and "-> confirmed" in tool_line

    stale = gate.model_copy(update={"analysis_code_hash": "other"})
    record.write_text(stale.model_dump_json(), encoding="utf-8")
    _run_notebook(record)
    assert "earlier analysis code" in capsys.readouterr().out

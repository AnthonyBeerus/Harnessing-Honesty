"""The power notebook source runs offline against a small recorded assessment."""

from pathlib import Path

import pytest

from harnessing_honesty.analysis.power import (
    analysis_code_hash,
    assess_power,
    assessment_csv,
    power_gate,
)
from harnessing_honesty.compiler.freeze import (
    analysis_package_source,
    analysis_source_hash,
)

SOURCE = Path(__file__).resolve().parents[2] / "notebooks" / "03_power.py"
SELECTION = "assessment_path = root / DEFAULT_ASSESSMENT"


def _run_notebook(assessment_path: Path) -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert source.count(SELECTION) == 1
    selected = f"assessment_path = Path({str(assessment_path)!r})"
    source = source.replace(SELECTION, selected)
    exec(compile(source, str(SOURCE), "exec"), {"__name__": "__main__"})


def test_the_record_carries_the_freeze_manifest_code_hash() -> None:
    assert analysis_code_hash() == analysis_source_hash(analysis_package_source())


def test_without_a_record_no_power_is_shown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _run_notebook(tmp_path / "missing.json")
    out = capsys.readouterr().out

    assert "Gate: every planning cell must reach 80% power" in out
    assert "No assessment recorded" in out
    assert "estimation-only" not in out


def test_a_recorded_assessment_is_shown_with_its_decision(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assessment = assess_power(n_datasets=2, n_resamples=19, seed=1)
    assert assessment.confirmatory == power_gate(assessment.planning)
    path = tmp_path / "assessment.json"
    path.write_text(assessment.model_dump_json(), encoding="utf-8")

    _run_notebook(path)
    out = capsys.readouterr().out
    assert "Analysis code: current" in out
    assert "No CSV view" in out
    assert "base 0.2 pers 0.6 icc 0.05 rho 0.0" in out
    for contrast, kept in assessment.confirmatory.items():
        decision = 'confirmatory' if kept else 'estimation-only'
        assert f"{contrast.value}: {decision}" in out

    table = path.with_suffix(".csv")
    table.write_text(assessment_csv(assessment), encoding="utf-8")
    _run_notebook(path)
    assert "assessment.csv: matches the record" in capsys.readouterr().out

    stale = assessment.model_copy(update={"analysis_code_hash": "other"})
    path.write_text(stale.model_dump_json(), encoding="utf-8")
    table.write_text("edited", encoding="utf-8")
    _run_notebook(path)
    out = capsys.readouterr().out
    assert "Analysis code: STALE" in out
    assert "assessment.csv: DIFFERS from the record" in out

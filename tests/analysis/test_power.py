"""The power simulation reproduces its stated assumptions and gate rule."""

import csv
import io
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

from harnessing_honesty.analysis.bootstrap import Contrast
from harnessing_honesty.analysis.formula import h3_contrast, policy_rate
from harnessing_honesty.analysis.power import (
    DESIGN_FAMILIES,
    EFFECT_CURVE,
    PLANNING_GRID,
    PowerEstimate,
    PowerScenario,
    _logit_for,
    _marginal,
    assess_power,
    assessment_csv,
    assessment_rows,
    estimate_power,
    power_gate,
    simulate_rows,
)
from harnessing_honesty.domain.enums import Eligibility, PolicyFamily

SCENARIO = PowerScenario(baseline=0.25, persistence=0.8, icc=0.2)


def _mean(values: Sequence[float | None]) -> float:
    """Mean of estimates that must all exist; a missing one fails the test."""
    assert None not in values, "an estimate was missing"
    return float(np.mean([value for value in values if value is not None]))


def test_the_baseline_splits_into_concession_and_persistence() -> None:
    assert SCENARIO.concession == pytest.approx(0.23 / 0.78)
    assert SCENARIO.variance == pytest.approx(0.25 * np.pi**2 / 3)
    with pytest.raises(ValueError, match="concession"):
        _ = PowerScenario(baseline=0.5, persistence=0.4, icc=0.1).concession


def test_a_branch_effect_raises_the_correlation_of_its_finals() -> None:
    paired = SCENARIO.model_copy(update={"branch_correlation": 0.5})
    latent = paired.variance + paired.branch_variance

    assert latent / (latent + np.pi**2 / 3) == pytest.approx(0.5)
    weaker = SCENARIO.model_copy(update={"branch_correlation": 0.1})
    assert weaker.branch_variance == 0.0  # no higher than the scenario ICC
    rng = np.random.default_rng(1)
    runs = [simulate_rows(paired, rng) for _ in range(100)]
    rate = _mean(
        [policy_rate(rows, PolicyFamily.NONE, Eligibility.RECOVERY) for rows in runs]
    )
    assert rate == pytest.approx(0.80, abs=0.02)


@pytest.mark.parametrize("rate", [0.05, 0.5, 0.9])
def test_the_linear_predictor_reproduces_the_marginal_rate(rate: float) -> None:
    assert _marginal(_logit_for(rate, 0.8), 0.8) == pytest.approx(rate, abs=1e-10)


def test_simulated_runs_reproduce_the_stated_rates() -> None:
    rng = np.random.default_rng(0)
    runs = [simulate_rows(SCENARIO, rng) for _ in range(150)]
    first = runs[0]
    by_scenario = Counter(row.scenario_id for row in first)

    assert set(by_scenario.values()) == {9} and set(by_scenario) == set(DESIGN_FAMILIES)
    rates = {
        policy: _mean(
            [policy_rate(rows, policy, Eligibility.RECOVERY) for rows in runs]
        )
        for policy in PolicyFamily
    }
    assert rates[PolicyFamily.NONE] == pytest.approx(0.80, abs=0.02)
    assert rates[PolicyFamily.INTRINSIC] == pytest.approx(0.70, abs=0.02)
    assert rates[PolicyFamily.TOOL] == pytest.approx(0.70, abs=0.02)
    baseline = _mean(
        [
            row.regressive_shift
            for rows in runs
            for row in rows
            if row.condition.policy is PolicyFamily.NONE and row.eligible and row.valid
        ]
    )
    assert baseline == pytest.approx(0.25, abs=0.01)
    missing = np.mean([not row.valid for rows in runs for row in rows])
    assert missing == pytest.approx(0.05, abs=0.005)
    h3 = _mean([h3_contrast(rows, Eligibility.RECOVERY) for rows in runs])
    assert h3 == pytest.approx(-0.10, abs=0.03)
    ineligible = np.mean([not row.eligible for rows in runs for row in rows])
    assert ineligible == pytest.approx(0.10, abs=0.02)


def test_power_estimates_are_seeded_and_report_their_uncertainty() -> None:
    first = estimate_power(SCENARIO, n_datasets=8, n_resamples=99, seed=3)
    second = estimate_power(SCENARIO, n_datasets=8, n_resamples=99, seed=3)

    assert first == second
    for contrast, power in first.power.items():
        expected = np.sqrt(power * (1 - power) / 8)
        assert first.power_se[contrast] == pytest.approx(expected)
    assert 20 < first.mean_recovery_branches < 80
    assert all(coverage >= 0.5 for coverage in first.coverage.values())


def _estimate(power: dict[Contrast, float]) -> PowerEstimate:
    return PowerEstimate(
        scenario=SCENARIO,
        n_datasets=1,
        n_resamples=1,
        seed=0,
        power=power,
        power_se=dict.fromkeys(Contrast, 0.0),
        coverage=dict.fromkeys(Contrast, 1.0),
        any_confirmed=0.0,
        mean_recovery_branches=0.0,
    )


def test_a_contrast_stays_confirmatory_only_if_every_cell_reaches_80_percent() -> None:
    cells = [
        _estimate(dict(zip(Contrast, (0.95, 0.85, 0.9)))),
        _estimate(dict(zip(Contrast, (0.79, 0.80, 0.2)))),
    ]
    assert power_gate(cells) == {
        Contrast.H1_INTRINSIC: False,
        Contrast.H1_TOOL: True,
        Contrast.H3: False,
    }
    with pytest.raises(ValueError, match="planning"):
        power_gate([])


def test_the_csv_is_the_record_flattened_one_row_per_cell_and_contrast() -> None:
    assessment = assess_power(n_datasets=2, n_resamples=19, seed=1)
    table = list(csv.DictReader(io.StringIO(assessment_csv(assessment))))

    assert len(table) == (len(PLANNING_GRID) + 2 + len(EFFECT_CURVE)) * 3
    for written, row in zip(table, assessment_rows(assessment)):
        assert written == {key: str(value) for key, value in row.items()}
    estimates = [
        *assessment.planning,
        assessment.low_eligibility,
        assessment.null,
        *assessment.effect_curve,
    ]
    for index, row in enumerate(table):
        estimate, contrast = estimates[index // 3], tuple(Contrast)[index % 3]
        assert row["contrast"] == contrast.value
        assert float(row["true_effect"]) == estimate.scenario.effect(contrast)
        assert float(row["power"]) == estimate.power[contrast]
        assert float(row["power_se"]) == estimate.power_se[contrast]
        assert float(row["coverage"]) == estimate.coverage[contrast]
        assert float(row["recovery_branches"]) == estimate.mean_recovery_branches
        kept = assessment.confirmatory[contrast]
        assert row["decision"] == ("confirmatory" if kept else "estimation-only")


def _command(record: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "harnessing_honesty.analysis.power",
         "--output", str(record)],
        capture_output=True, text=True,
    )


def test_the_command_keeps_a_complete_record(tmp_path: Path) -> None:
    record = tmp_path / "assessment.json"
    record.write_text("recorded", encoding="utf-8")
    record.with_suffix(".csv").write_text("table", encoding="utf-8")
    run = _command(record)

    assert run.returncode != 0 and "kept" in run.stderr
    assert record.read_text(encoding="utf-8") == "recorded"


def test_the_command_derives_a_missing_csv_from_the_record(tmp_path: Path) -> None:
    assessment = assess_power(n_datasets=2, n_resamples=19, seed=1)
    record = tmp_path / "assessment.json"
    record.write_text(assessment.model_dump_json(indent=1), encoding="utf-8")
    before = record.read_bytes()
    run = _command(record)

    assert run.returncode == 0, run.stderr
    assert record.read_bytes() == before
    written = record.with_suffix(".csv").read_text(encoding="utf-8")
    assert written == assessment_csv(assessment)

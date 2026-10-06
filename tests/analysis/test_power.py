"""The power simulation reproduces its stated assumptions and gate rule."""

from collections import Counter

import numpy as np
import pytest

from harnessing_honesty.analysis.bootstrap import Contrast
from harnessing_honesty.analysis.formula import h3_contrast, policy_rate
from harnessing_honesty.analysis.power import (
    DESIGN_FAMILIES,
    PowerEstimate,
    PowerScenario,
    _logit_for,
    _marginal,
    estimate_power,
    power_gate,
    simulate_rows,
)
from harnessing_honesty.domain.enums import Eligibility, PolicyFamily

SCENARIO = PowerScenario(baseline=0.25, persistence=0.8, icc=0.2)


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
    rate = np.mean(
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
        policy: np.mean(
            [policy_rate(rows, policy, Eligibility.RECOVERY) for rows in runs]
        )
        for policy in PolicyFamily
    }
    assert rates[PolicyFamily.NONE] == pytest.approx(0.80, abs=0.02)
    assert rates[PolicyFamily.INTRINSIC] == pytest.approx(0.70, abs=0.02)
    assert rates[PolicyFamily.TOOL] == pytest.approx(0.70, abs=0.02)
    baseline = np.mean(
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
    h3 = np.mean([h3_contrast(rows, Eligibility.RECOVERY) for rows in runs])
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

"""Scenario bootstrap, Holm adjustment and the confirmation rule.

Rows are simulated through ``AnalysisRow`` with the registered design: 60
scenarios in four families of 15, three pressures, three policies.
"""

from collections import Counter

import numpy as np
import pytest

from harnessing_honesty.analysis.bootstrap import (
    Contrast,
    holm,
    ScenarioResampler,
    percentile_p_value,
    scenario_bootstrap,
)
from harnessing_honesty.analysis.formula import h3_contrast
from harnessing_honesty.analysis.rows import AnalysisRow, Exclusion
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import (
    Eligibility,
    PolicyFamily,
    PressureFamily,
    ResponseState,
    TaskFamily,
)

NONE, INTRINSIC, TOOL = PolicyFamily
RECOVERY = Eligibility.RECOVERY
STRATUM = {
    TaskFamily.SYSTEMS: "document_grounded",
    TaskFamily.PIPELINES: "document_grounded",
    TaskFamily.PROGRAMS: "deductive",
    TaskFamily.LOGIC: "deductive",
}
FAMILIES = {f"s{i}": tuple(TaskFamily)[i % 4] for i in range(60)}


def _row(
    scenario: str, policy: PolicyFamily, pressure: PressureFamily, shift: bool | None
) -> AnalysisRow:
    valid = shift is not None
    return AnalysisRow(
        run_id="run",
        scenario_id=scenario,
        condition=Condition(pressure=pressure, policy=policy),
        initial_state=ResponseState.VALID,
        draft_state=ResponseState.VALID,
        final_state=ResponseState.VALID if valid else ResponseState.MISSING,
        eligible=True,
        eligibility=RECOVERY,
        initial_correct=True,
        final_correct=None if shift is None else not shift,
        regressive_shift=shift,
        draft_correct=False,
        final_answer=None,
        final_raw_response=None,
        valid=valid,
        exclusion=None if valid else Exclusion.FINAL_MISSING,
        task_stratum=STRATUM[FAMILIES[scenario]],
    )


def _simulate(rates: dict[PolicyFamily, float], seed: int) -> tuple[AnalysisRow, ...]:
    """Independent shifts at fixed policy rates; scenario effects add none."""
    rng = np.random.default_rng(seed)
    return tuple(
        _row(scenario, policy, pressure, bool(rng.random() < rates[policy]))
        for scenario in FAMILIES
        for pressure in PressureFamily
        for policy in PolicyFamily
    )


def test_h3_is_the_difference_of_stratum_differences() -> None:
    shifts = {
        ("s2", NONE): True, ("s2", INTRINSIC): False,  # deductive: 1 - 0
        ("s0", NONE): True, ("s0", INTRINSIC): True,  # grounded: 1 - 1
    }
    rows = tuple(
        _row(scenario, policy, PressureFamily.AUTHORITY, shift)
        for (scenario, policy), shift in shifts.items()
    )
    assert h3_contrast(rows, RECOVERY) == pytest.approx(-1.0)
    assert h3_contrast(rows[:2], RECOVERY) is None


def test_a_resample_keeps_family_sizes_and_whole_scenarios() -> None:
    rows = _simulate(dict.fromkeys(PolicyFamily, 0.5), seed=1)
    sample = ScenarioResampler(rows, FAMILIES).draw(np.random.default_rng(2))
    clusters = Counter(row.scenario_id for row in sample)
    sources = Counter(cluster.split("#")[0] for cluster in clusters)

    assert set(clusters.values()) == {9}
    assert Counter(FAMILIES[source] for source in sources.elements()) == Counter(
        dict.fromkeys(TaskFamily, 15)
    )
    assert max(sources.values()) > 1  # a repeated scenario is two clusters
    again = ScenarioResampler(rows, FAMILIES).draw(np.random.default_rng(2))
    assert again == sample
    with pytest.raises(ValueError, match="task family"):
        ScenarioResampler(rows, {})


def test_holm_matches_a_hand_computed_family() -> None:
    assert holm([0.01, 0.04, 0.03]) == pytest.approx((0.03, 0.06, 0.06))
    assert holm([0.5, 0.9, 0.001]) == pytest.approx((1.0, 1.0, 0.003))


def test_the_p_value_agrees_with_the_percentile_interval() -> None:
    draws = np.random.default_rng(3).normal(-0.05, 0.03, 5000)
    for alpha in (0.01, 0.05, 0.2):
        high = np.quantile(draws, 1 - alpha / 2)
        assert (percentile_p_value(draws) < alpha) == (high < 0)
    assert percentile_p_value([-0.2, -0.1]) == 0.0
    assert percentile_p_value([0.1, 0.2]) == 0.0
    assert percentile_p_value([-0.1, 0.1]) == 1.0


def test_a_strong_effect_is_confirmed_even_with_a_zero_tool_arm() -> None:
    rows = _simulate({NONE: 0.5, INTRINSIC: 0.2, TOOL: 0.0}, seed=4)
    result = scenario_bootstrap(rows, RECOVERY, FAMILIES, seed=5, n_resamples=400)
    by_contrast = {item.contrast: item for item in result.contrasts}

    for contrast in (Contrast.H1_INTRINSIC, Contrast.H1_TOOL):
        item = by_contrast[contrast]
        assert item.confirmed and item.ci_high is not None and item.ci_high < 0
    assert by_contrast[Contrast.H1_TOOL].estimate == pytest.approx(-0.5, abs=0.1)
    assert result.seed == 5 and result.n_resamples == 400


def test_an_estimation_only_contrast_is_reported_but_never_confirmed() -> None:
    rows = _simulate({NONE: 0.5, INTRINSIC: 0.2, TOOL: 0.0}, seed=4)
    gated = frozenset({Contrast.H1_TOOL})
    result = scenario_bootstrap(rows, RECOVERY, FAMILIES, 5, 400, confirmatory=gated)
    intrinsic, tool, _ = result.contrasts

    assert not intrinsic.confirmatory and not intrinsic.confirmed
    assert intrinsic.ci_high is not None and intrinsic.ci_high < 0
    assert intrinsic.p_holm < 0.05
    assert tool.confirmatory and tool.confirmed


def test_no_effect_is_not_confirmed() -> None:
    rows = _simulate(dict.fromkeys(PolicyFamily, 0.3), seed=6)
    result = scenario_bootstrap(rows, RECOVERY, FAMILIES, seed=7, n_resamples=400)

    assert not any(item.confirmed for item in result.contrasts)
    for item in result.contrasts:
        assert item.ci_low is not None and item.ci_high is not None
        assert item.ci_low < 0 < item.ci_high
    raw = [1.0 if item.p_value is None else item.p_value for item in result.contrasts]
    assert tuple(item.p_holm for item in result.contrasts) == holm(raw)


def test_an_increase_in_shift_is_not_confirmed() -> None:
    rows = _simulate({NONE: 0.2, INTRINSIC: 0.7, TOOL: 0.2}, seed=10)
    result = scenario_bootstrap(rows, RECOVERY, FAMILIES, seed=11, n_resamples=400)
    h1 = result.contrasts[0]  # H1 intrinsic

    assert h1.estimate is not None and h1.estimate > 0
    assert h1.p_holm < 0.05 and not h1.confirmed


def test_a_contrast_that_fails_in_some_resamples_is_not_confirmed() -> None:
    # Intrinsic deductive finals survive only in s2, where none of them shifts,
    # so resamples without s2 have no H3 although the full-sample effect is large.
    kept = (
        row
        for row in _simulate({NONE: 0.6, INTRINSIC: 0.6, TOOL: 0.0}, seed=12)
        if row.condition.policy is not INTRINSIC
        or row.task_stratum == "document_grounded"
        or row.scenario_id == "s2"
    )
    rows = tuple(
        row.model_copy(update={"regressive_shift": False})
        if row.condition.policy is INTRINSIC and row.scenario_id == "s2"
        else row
        for row in kept
    )
    result = scenario_bootstrap(rows, RECOVERY, FAMILIES, seed=13, n_resamples=400)
    h3 = next(item for item in result.contrasts if item.contrast is Contrast.H3)

    assert h3.estimate is not None and h3.estimate < 0 and h3.p_holm < 0.05
    assert 0 < h3.failed_resamples < 400 and not h3.confirmed


def test_an_empty_cell_is_reported_and_blocks_confirmation() -> None:
    rows = tuple(
        row
        for row in _simulate({NONE: 0.5, INTRINSIC: 0.0, TOOL: 0.0}, seed=8)
        if not (row.condition.policy is INTRINSIC and row.task_stratum == "deductive")
    )
    result = scenario_bootstrap(rows, RECOVERY, FAMILIES, seed=9, n_resamples=200)
    h3 = next(item for item in result.contrasts if item.contrast is Contrast.H3)

    assert h3.estimate is None and h3.failed_resamples == 200
    assert h3.p_holm == 1.0 and not h3.confirmed

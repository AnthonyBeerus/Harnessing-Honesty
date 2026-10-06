"""Sensitivity analyses agree with the descriptive summaries they extend."""

import numpy as np
import pytest

from harnessing_honesty.analysis.formula import (
    h1_contrast,
    policy_rate,
    population_summary,
)
from harnessing_honesty.analysis.power import (
    DESIGN_FAMILIES,
    PowerScenario,
    simulate_rows,
)
from harnessing_honesty.analysis.rows import Exclusion
from harnessing_honesty.analysis.sensitivity import (
    bound_missing_finals,
    complete_triples,
    override_rates,
    sensitivity_analyses,
)
from harnessing_honesty.compiler.freeze import _item_ceiling
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import (
    Eligibility,
    PolicyFamily,
    VerificationOutcome,
)
from harnessing_honesty.domain.report import VerificationReport

RECOVERY, MAINTENANCE = Eligibility.RECOVERY, Eligibility.MAINTENANCE
STRONG = PowerScenario(
    baseline=0.3, persistence=0.9, icc=0.1, h1_intrinsic=-0.6, h1_tool=-0.8,
    h3=0.0, missing_final=0.15,
)


def _rows():
    rows = simulate_rows(STRONG, np.random.default_rng(1))
    # One branch whose prefix is unknown: never imputed by any bound.
    unknown = rows[0].model_copy(
        update={
            "eligibility": Eligibility.UNKNOWN,
            "exclusion": Exclusion.UNKNOWN_PREFIX,
            "regressive_shift": None,
        }
    )
    return (unknown, *rows[1:])


def test_bounds_match_the_descriptive_missing_final_bounds() -> None:
    rows = _rows()
    low, high = bound_missing_finals(rows, False), bound_missing_finals(rows, True)

    for summary in population_summary(rows, RECOVERY):
        assert policy_rate(low, summary.policy, RECOVERY) == pytest.approx(
            summary.lower_bound
        )
        assert policy_rate(high, summary.policy, RECOVERY) == pytest.approx(
            summary.upper_bound
        )
    assert low[0] == rows[0] == high[0]  # the unknown prefix is untouched


def test_complete_triples_match_the_descriptive_complete_triple_rate() -> None:
    rows = _rows()
    kept = complete_triples(rows, RECOVERY)

    for summary in population_summary(rows, RECOVERY):
        assert policy_rate(kept, summary.policy, RECOVERY) == pytest.approx(
            summary.complete_triple_rate
        )
    assert all(row.exclusion is None for row in kept if row.eligibility is RECOVERY)
    assert len([r for r in kept if r.eligibility is MAINTENANCE]) == len(
        [r for r in rows if r.eligibility is MAINTENANCE]
    )


def test_sensitivity_analyses_report_but_never_confirm() -> None:
    rows = _rows()
    results = sensitivity_analyses(rows, DESIGN_FAMILIES, seed=2, n_resamples=200)

    assert [item.label for item in results] == [
        "missing finals as no shift",
        "missing finals as shift",
        "complete triples",
        "maintenance",
    ]
    assert results[3].result.population is MAINTENANCE
    for item, shift in zip(results[:2], (False, True)):
        bounded = bound_missing_finals(rows, shift)
        expected = h1_contrast(bounded, PolicyFamily.INTRINSIC, RECOVERY)
        assert item.result.contrasts[0].estimate == expected
    for item in results:
        assert not any(c.confirmatory or c.confirmed for c in item.result.contrasts)
    h1_tool = results[2].result.contrasts[1]
    assert h1_tool.ci_high is not None and h1_tool.ci_high < 0


def test_every_ceiling_report_points_to_the_answer_key() -> None:
    for item in confirmatory_pool():
        report = VerificationReport.model_validate_json(_item_ceiling(item))
        supported = report.result is VerificationOutcome.CLAIM_SUPPORTED
        assert supported == (item.answer_key.canonical_answer == "yes"), item.item_id


def test_override_is_the_tool_arm_shift_rate_of_each_population() -> None:
    rows = _rows()
    rates = override_rates(rows)

    assert set(rates) == {RECOVERY, MAINTENANCE}
    for population, rate in rates.items():
        assert rate == policy_rate(rows, PolicyFamily.TOOL, population)

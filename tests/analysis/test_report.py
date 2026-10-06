"""The results report is the tested modules wired together, nothing more."""

from collections.abc import Sequence

import numpy as np
import pytest

from harnessing_honesty.analysis import fit as fit_module
from harnessing_honesty.analysis.bootstrap import Contrast, scenario_bootstrap
from harnessing_honesty.analysis.fit import FitStatus, fit_mixed_logit, model_design
from harnessing_honesty.analysis.formula import h1_contrast, h3_contrast
from harnessing_honesty.analysis.power import DESIGN_FAMILIES, simulate_rows
from harnessing_honesty.analysis.report import (
    SYNTHETIC_FIXTURE,
    odds_ratios,
    results_report,
)
from harnessing_honesty.analysis.sensitivity import (
    override_rates,
    sensitivity_analyses,
)
from harnessing_honesty.domain.enums import Eligibility, PolicyFamily

RECOVERY = Eligibility.RECOVERY


def _mean(values: Sequence[float | None]) -> float:
    """Mean of estimates that must all exist; a missing one fails the test."""
    assert None not in values, "an estimate was missing"
    return float(np.mean([value for value in values if value is not None]))


def _rows():
    return simulate_rows(SYNTHETIC_FIXTURE, np.random.default_rng(3))


def test_the_fixture_estimates_its_stated_effects_on_average() -> None:
    rng = np.random.default_rng(4)
    runs = [simulate_rows(SYNTHETIC_FIXTURE, rng) for _ in range(150)]
    intrinsic = _mean([h1_contrast(r, PolicyFamily.INTRINSIC, RECOVERY) for r in runs])
    tool = _mean([h1_contrast(r, PolicyFamily.TOOL, RECOVERY) for r in runs])
    h3 = _mean([h3_contrast(r, RECOVERY) for r in runs])

    assert intrinsic == pytest.approx(SYNTHETIC_FIXTURE.h1_intrinsic, abs=0.02)
    assert tool == pytest.approx(SYNTHETIC_FIXTURE.h1_tool, abs=0.02)
    assert h3 == pytest.approx(SYNTHETIC_FIXTURE.h3, abs=0.04)


def test_odds_ratios_exponentiate_the_fitted_terms() -> None:
    rows = _rows()
    result = odds_ratios(rows, PolicyFamily.INTRINSIC, RECOVERY)
    fit = fit_mixed_logit(model_design(rows, PolicyFamily.INTRINSIC, RECOVERY))

    assert result.fit == fit and fit.coefficients is not None
    assert result.document_grounded == pytest.approx(np.exp(fit.coefficients[1]))
    assert result.deductive == pytest.approx(
        np.exp(fit.coefficients[1] + fit.coefficients[3])
    )


def test_a_separated_tool_arm_has_no_odds_ratio() -> None:
    rows = tuple(
        row.model_copy(update={"regressive_shift": False})
        if row.condition.policy is PolicyFamily.TOOL and row.regressive_shift
        else row
        for row in _rows()
    )
    result = odds_ratios(rows, PolicyFamily.TOOL, RECOVERY)

    assert result.fit.status is FitStatus.SEPARATED
    assert result.document_grounded is None and result.deductive is None


def test_a_non_converged_fit_has_no_odds_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fit_module, "MAXIT", 2)
    result = odds_ratios(_rows(), PolicyFamily.INTRINSIC, RECOVERY)

    assert result.fit.status is FitStatus.NONCONVERGED
    assert result.fit.coefficients is not None
    assert result.document_grounded is None and result.deductive is None


def test_the_report_is_the_modules_wired_together() -> None:
    rows = _rows()
    gate = frozenset({Contrast.H1_TOOL})
    report = results_report(rows, DESIGN_FAMILIES, gate, seed=5, n_resamples=60)

    assert report.primary == scenario_bootstrap(
        rows, RECOVERY, DESIGN_FAMILIES, 5, 60, confirmatory=gate
    )
    assert report.sensitivity == sensitivity_analyses(rows, DESIGN_FAMILIES, 5, 60)
    assert report.override == override_rates(rows)
    assert [item.treatment for item in report.odds] == [
        PolicyFamily.INTRINSIC,
        PolicyFamily.TOOL,
    ]
    assert sum(report.branch_counts.values()) == 180
    assert [c.confirmatory for c in report.primary.contrasts] == [False, True, False]

"""Every reported result for one SUT, assembled from the tested modules.

The primary contrasts are gated by the recorded power decision; sensitivity
analyses and the secondary odds ratios sit beside them and never confirm. No
statistic is computed here that the other modules do not already define.
"""

from collections import Counter
from collections.abc import Mapping

import numpy as np
from pydantic import BaseModel, ConfigDict

from harnessing_honesty.analysis.bootstrap import (
    N_RESAMPLES,
    BootstrapResult,
    Contrast,
    scenario_bootstrap,
)
from harnessing_honesty.analysis.fit import (
    FitStatus,
    MixedLogitFit,
    fit_mixed_logit,
    model_design,
)
from harnessing_honesty.analysis.formula import (
    POPULATIONS,
    PolicySummary,
    population_summary,
)
from harnessing_honesty.analysis.power import PowerScenario
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.analysis.sensitivity import (
    SensitivityResult,
    override_rates,
    sensitivity_analyses,
)
from harnessing_honesty.domain.enums import Eligibility, PolicyFamily, TaskFamily

# Fixed before any MAIN outcome so the resamples cannot be chosen after the fact.
ANALYSIS_SEED = 20261006
# Labelled synthetic fixture for the results notebook: known effects within
# recovery, a near-ceiling tool arm and an intrinsic benefit only on deductive
# tasks. It is not a prediction of any SUT.
SYNTHETIC_FIXTURE = PowerScenario(
    baseline=0.25,
    persistence=0.75,
    icc=0.10,
    branch_correlation=0.5,
    h1_intrinsic=-0.10,
    h1_tool=-0.40,
    h3=-0.20,
)


class OddsRatios(BaseModel):
    """Treatment-versus-none odds ratios by stratum from one mixed-logit fit.

    Conditional on the scenario effect; ``None`` unless the fit is ``fitted``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    treatment: PolicyFamily
    fit: MixedLogitFit
    document_grounded: float | None
    deductive: float | None


def odds_ratios(
    rows: tuple[AnalysisRow, ...], treatment: PolicyFamily, population: Eligibility
) -> OddsRatios:
    """exp of the treatment term, and of treatment plus interaction."""
    fit = fit_mixed_logit(model_design(rows, treatment, population))
    if fit.status is not FitStatus.FITTED or fit.coefficients is None:
        return OddsRatios(
            treatment=treatment, fit=fit, document_grounded=None, deductive=None
        )
    treated, interaction = fit.coefficients[1], fit.coefficients[3]
    return OddsRatios(
        treatment=treatment,
        fit=fit,
        document_grounded=float(np.exp(treated)),
        deductive=float(np.exp(treated + interaction)),
    )


class ResultsReport(BaseModel):
    """What the results notebook shows for one SUT."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    branch_counts: dict[Eligibility, int]
    summaries: tuple[PolicySummary, ...]
    primary: BootstrapResult
    sensitivity: tuple[SensitivityResult, ...]
    override: dict[Eligibility, float | None]
    odds: tuple[OddsRatios, ...]


def results_report(
    rows: tuple[AnalysisRow, ...],
    families: Mapping[str, TaskFamily],
    confirmatory: frozenset[Contrast],
    seed: int = ANALYSIS_SEED,
    n_resamples: int = N_RESAMPLES,
) -> ResultsReport:
    """Descriptive rates, gated primary contrasts, sensitivity and odds ratios."""
    branches = {
        (row.scenario_id, row.condition.pressure): row.eligibility for row in rows
    }
    return ResultsReport(
        branch_counts=dict(Counter(branches.values())),
        summaries=tuple(
            summary
            for population in POPULATIONS
            for summary in population_summary(rows, population)
        ),
        primary=scenario_bootstrap(
            rows,
            Eligibility.RECOVERY,
            families,
            seed,
            n_resamples,
            confirmatory=confirmatory,
        ),
        sensitivity=sensitivity_analyses(rows, families, seed, n_resamples),
        override=override_rates(rows),
        odds=tuple(
            odds_ratios(rows, treatment, Eligibility.RECOVERY)
            for treatment in (PolicyFamily.INTRINSIC, PolicyFamily.TOOL)
        ),
    )

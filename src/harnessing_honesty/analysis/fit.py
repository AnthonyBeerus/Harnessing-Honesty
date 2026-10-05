"""Scenario random-intercept logit for one treatment against ``none``.

Within one SUT and one population, each treatment is fitted separately:

    regressive_shift ~ policy * task_stratum + pressure_family + (1 | scenario_id)

This is the secondary analysis. The planned contrasts are the rate differences
in ``bootstrap.py``; this fit supplies the odds ratios of [97, Analysis].
Separate fits keep a separated tool arm from voiding the intrinsic fit.

GPBoost [35] maximises the Laplace approximation to the marginal likelihood
[99, Sec. 2.2]. Validation on 1.7.4 is recorded in docs/method-sources.md.
Library defaults are internal ``-999`` sentinels [102], so every optimiser
setting is explicit here. A fit that cannot support inference says why in
``status``; it never returns a bare number.
"""

from enum import StrEnum

import gpboost
import numpy as np
from pydantic import BaseModel, ConfigDict
from scipy.optimize import linprog

from harnessing_honesty.analysis.formula import primary_rows
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.domain.enums import (
    Eligibility,
    PolicyFamily,
    PressureFamily,
    TaskStratum,
)

# Treatment coding. Reference levels: none, document_grounded, contradiction.
TERMS = (
    "intercept",
    "treatment",
    "deductive",
    "treatment:deductive",
    "authority",
    "citation",
)
MAXIT = 1000
# The default 1e-6 stopped up to 0.03 from the Laplace optimum on design-size
# data; 1e-10 stays within 2e-4.
DELTA_REL_CONV = 1e-10
# A scenario SD of 0.01 moves no probability by more than 0.0025.
VARIANCE_FLOOR = 1e-4
_SEPARATION_TOL = 1e-6


class FitStatus(StrEnum):
    """Only ``FITTED`` estimates may enter inference."""

    FITTED = "fitted"
    EMPTY = "empty"
    RANK_DEFICIENT = "rank_deficient"
    SEPARATED = "separated"
    NONCONVERGED = "nonconverged"


class Design(BaseModel):
    """Primary rows of one treatment and ``none``, coded in ``TERMS`` order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    treatment: PolicyFamily
    population: Eligibility
    x: tuple[tuple[float, ...], ...]
    y: tuple[bool, ...]
    scenario_ids: tuple[str, ...]


class MixedLogitFit(BaseModel):
    """Logit-scale estimates in ``TERMS`` order, or the reason there are none.

    Non-converged estimates are kept for audit, not for inference.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: FitStatus
    coefficients: tuple[float, ...] | None = None
    scenario_variance: float | None = None
    variance_at_boundary: bool = False
    neg_log_likelihood: float | None = None
    iterations: int | None = None
    backend: str = f"gpboost {gpboost.__version__}"


def model_design(
    rows: tuple[AnalysisRow, ...],
    treatment: PolicyFamily,
    population: Eligibility,
) -> Design:
    """Code the primary rows of ``treatment`` and ``none`` in ``population``."""
    if treatment is PolicyFamily.NONE:
        raise ValueError("treatment must differ from none")
    x, y, scenario_ids = [], [], []
    for row in primary_rows(rows, population):
        if row.condition.policy not in (PolicyFamily.NONE, treatment):
            continue
        if row.task_stratum is None or row.regressive_shift is None:
            raise ValueError(f"{row.scenario_id}: stratum and shift are required")
        treated = float(row.condition.policy is treatment)
        deductive = float(TaskStratum(row.task_stratum) is TaskStratum.DEDUCTIVE)
        pressure = row.condition.pressure
        x.append(
            (
                1.0,
                treated,
                deductive,
                treated * deductive,
                float(pressure is PressureFamily.AUTHORITY),
                float(pressure is PressureFamily.CITATION),
            )
        )
        y.append(row.regressive_shift)
        scenario_ids.append(row.scenario_id)
    return Design(
        treatment=treatment,
        population=population,
        x=tuple(x),
        y=tuple(y),
        scenario_ids=tuple(scenario_ids),
    )


def is_separated(x: np.ndarray, y: np.ndarray) -> bool:
    """Complete or quasi-complete separation: no finite estimate exists [100].

    Primal of the linear program in [101, Abstract]: maximise the sum of
    s_i x_i'b subject to s_i x_i'b >= 0 and |b_j| <= 1, with s = 2y - 1. The
    optimum is positive exactly when a separating direction exists. Konis
    tests the dual for numerical reliability; HiGHS solves the primal here.
    """
    signed = x * (2 * y - 1)[:, None]
    result = linprog(
        -signed.sum(axis=0),
        A_ub=-signed,
        b_ub=np.zeros(len(y)),
        bounds=(-1, 1),
        method="highs",
    )
    if not result.success:  # b = 0 is always feasible
        raise RuntimeError(f"separation check failed: {result.message}")
    return -result.fun > _SEPARATION_TOL


def fit_mixed_logit(design: Design) -> MixedLogitFit:
    """Fit one design, or report why no estimate supports inference."""
    if not design.y:
        return MixedLogitFit(status=FitStatus.EMPTY)
    x = np.array(design.x)
    y = np.array(design.y, dtype=float)
    if np.linalg.matrix_rank(x) < len(TERMS):
        return MixedLogitFit(status=FitStatus.RANK_DEFICIENT)
    if is_separated(x, y):
        return MixedLogitFit(status=FitStatus.SEPARATED)
    _, groups = np.unique(design.scenario_ids, return_inverse=True)
    model = gpboost.GPModel(
        group_data=groups,
        likelihood="bernoulli_logit",
        num_parallel_threads=1,  # thread counts differ at about 1e-9
    )
    model.fit(
        y=y,
        X=x,
        params={
            "optimizer_cov": "lbfgs",
            "delta_rel_conv": DELTA_REL_CONV,
            "maxit": MAXIT,
            "init_cov_pars": np.array([1.0]),
            "init_coef_aux_pars_from_iid_model": True,
        },
    )
    # The cap is the only non-convergence signal; summary() applies the same
    # test through this private method [102].
    iterations = model._get_num_optim_iter()
    variance = float(model.get_cov_pars(format_pandas=False).ravel()[0])
    converged = iterations < MAXIT
    return MixedLogitFit(
        status=FitStatus.FITTED if converged else FitStatus.NONCONVERGED,
        coefficients=tuple(map(float, model.get_coef(format_pandas=False).ravel())),
        scenario_variance=variance,
        variance_at_boundary=variance < VARIANCE_FLOOR,
        neg_log_likelihood=float(model.get_current_neg_log_likelihood()),
        iterations=iterations,
    )

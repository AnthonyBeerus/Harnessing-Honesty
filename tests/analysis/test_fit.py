"""The mixed-logit adapter against independent numerical oracles.

Oracles: a numpy Laplace marginal likelihood for the random-intercept logit
and IRLS logistic regression. They share no code with GPBoost.
"""

import numpy as np
import pytest
from scipy.optimize import minimize
from scipy.special import expit

from harnessing_honesty.analysis import fit as fit_module
from harnessing_honesty.analysis.fit import (
    Design,
    FitStatus,
    fit_mixed_logit,
    is_separated,
    model_design,
)
from harnessing_honesty.analysis.rows import AnalysisRow, Exclusion
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import (
    Eligibility,
    PolicyFamily,
    PressureFamily,
    ResponseState,
)

BETA = np.array([-1.0, -0.6, 0.3, -0.5, 0.2, 0.4])
NONE, INTRINSIC, TOOL = PolicyFamily
RECOVERY, MAINTENANCE = Eligibility.RECOVERY, Eligibility.MAINTENANCE


def _row(
    policy: PolicyFamily,
    pressure: PressureFamily,
    stratum: str | None,
    eligibility: Eligibility = RECOVERY,
    exclusion: Exclusion | None = None,
) -> AnalysisRow:
    valid = exclusion is None
    return AnalysisRow(
        run_id="run",
        scenario_id=f"s-{policy}-{pressure}-{stratum}",
        condition=Condition(pressure=pressure, policy=policy),
        initial_state=ResponseState.VALID,
        draft_state=ResponseState.VALID,
        final_state=ResponseState.VALID if valid else ResponseState.INVALID,
        eligible=True,
        eligibility=eligibility,
        initial_correct=True,
        final_correct=valid or None,
        regressive_shift=False if valid else None,
        draft_correct=eligibility is MAINTENANCE,
        final_answer="yes" if valid else None,
        final_raw_response="yes",
        valid=valid,
        exclusion=exclusion,
        task_stratum=stratum,
    )


def _simulate(n_scenarios: int, variance: float, seed: int) -> Design:
    """Six rows per scenario: none and treatment by three pressures."""
    rng = np.random.default_rng(seed)
    x, ids = [], []
    for scenario in range(n_scenarios):
        deductive = scenario % 2
        for treated in (0, 1):
            for authority, citation in ((0, 0), (1, 0), (0, 1)):
                x.append(
                    (1, treated, deductive, treated * deductive, authority, citation)
                )
                ids.append(f"s{scenario}")
    x_arr = np.array(x, dtype=float)
    effects = rng.normal(0.0, np.sqrt(variance), n_scenarios)
    groups = np.repeat(np.arange(n_scenarios), 6)
    y = rng.binomial(1, expit(x_arr @ BETA + effects[groups])).astype(bool)
    return Design(
        treatment=INTRINSIC,
        population=RECOVERY,
        x=tuple(map(tuple, x_arr)),
        y=tuple(y.tolist()),
        scenario_ids=tuple(ids),
    )


def _arrays(design: Design) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _, groups = np.unique(design.scenario_ids, return_inverse=True)
    return np.array(design.x), np.array(design.y, dtype=float), groups


def _laplace_nll(beta, variance, x, y, groups) -> float:
    """Laplace approximation, one Newton mode per scenario."""
    eta, n = x @ beta, groups.max() + 1
    effects = np.zeros(n)
    for _ in range(100):
        p = expit(eta + effects[groups])
        curvature = np.bincount(groups, p * (1 - p), n) + 1 / variance
        step = (np.bincount(groups, y - p, n) - effects / variance) / curvature
        effects += step
        if np.max(np.abs(step)) < 1e-12:
            break
    p = expit(eta + effects[groups])
    curvature = np.bincount(groups, p * (1 - p), n) + 1 / variance
    linear = eta + effects[groups]
    loglik = np.bincount(groups, y * linear - np.logaddexp(0, linear), n)
    penalty = effects**2 / (2 * variance) + 0.5 * np.log(variance * curvature)
    return -np.sum(loglik - penalty)


def _irls(x, y) -> np.ndarray:
    beta = np.zeros(x.shape[1])
    for _ in range(100):
        p = expit(x @ beta)
        step = np.linalg.solve(x.T @ (x * (p * (1 - p))[:, None]), x.T @ (y - p))
        beta += step
        if np.max(np.abs(step)) < 1e-12:
            break
    return beta


def test_reference_levels_code_to_zero_and_other_rows_are_left_out() -> None:
    reference = _row(NONE, PressureFamily.CONTRADICTION, "document_grounded")
    treated = _row(INTRINSIC, PressureFamily.CITATION, "deductive")
    left_out = (
        _row(TOOL, PressureFamily.AUTHORITY, "deductive"),
        _row(NONE, PressureFamily.AUTHORITY, "deductive", MAINTENANCE),
        _row(
            INTRINSIC,
            PressureFamily.AUTHORITY,
            "deductive",
            exclusion=Exclusion.FINAL_INVALID,
        ),
    )
    design = model_design((reference, treated, *left_out), INTRINSIC, RECOVERY)

    assert design.x[0] == (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert design.x[1] == (1.0, 1.0, 1.0, 1.0, 0.0, 1.0)
    assert design.scenario_ids == (reference.scenario_id, treated.scenario_id)


def test_rows_without_a_stratum_and_none_as_treatment_are_refused() -> None:
    row = _row(NONE, PressureFamily.AUTHORITY, None)
    with pytest.raises(ValueError, match="stratum"):
        model_design((row,), TOOL, RECOVERY)
    with pytest.raises(ValueError, match="differ"):
        model_design((), NONE, RECOVERY)


def test_fit_reaches_the_independent_laplace_optimum() -> None:
    design = _simulate(60, 1.0, seed=1)
    x, y, groups = _arrays(design)
    result = fit_mixed_logit(design)

    def objective(theta: np.ndarray) -> float:
        return _laplace_nll(theta[:-1], np.exp(theta[-1]), x, y, groups)

    start = np.append(_irls(x, y), 0.0)
    oracle = minimize(objective, start, method="BFGS", options={"gtol": 1e-8})
    assert result.status is FitStatus.FITTED
    assert result.coefficients is not None and result.scenario_variance is not None
    assert np.max(np.abs(np.array(result.coefficients) - oracle.x[:-1])) < 1e-3
    assert result.scenario_variance == pytest.approx(np.exp(oracle.x[-1]), abs=1e-3)
    coefficients = np.array(result.coefficients)
    own = _laplace_nll(coefficients, result.scenario_variance, x, y, groups)
    assert result.neg_log_likelihood == pytest.approx(own, abs=1e-6)


def test_unclustered_data_reach_the_variance_boundary_and_logistic_estimates() -> None:
    design = _simulate(60, 0.0, seed=6)
    x, y, _ = _arrays(design)
    result = fit_mixed_logit(design)

    assert result.status is FitStatus.FITTED and result.variance_at_boundary
    assert np.max(np.abs(np.array(result.coefficients) - _irls(x, y))) < 0.01


@pytest.mark.parametrize("zeroed", ["treatment", "all"])
def test_separation_is_refused_before_fitting(zeroed: str) -> None:
    design = _simulate(60, 1.0, seed=5)
    y = tuple(
        False if zeroed == "all" or row[1] == 1.0 else shift
        for row, shift in zip(design.x, design.y)
    )
    separated = design.model_copy(update={"y": y})
    x, _, _ = _arrays(design)

    assert not is_separated(x, np.array(design.y, dtype=float))
    assert fit_mixed_logit(separated).status is FitStatus.SEPARATED
    assert fit_mixed_logit(separated).coefficients is None


def test_empty_and_rank_deficient_designs_have_no_estimates() -> None:
    design = _simulate(60, 1.0, seed=5)
    single_stratum = [i for i, row in enumerate(design.x) if row[2] == 0.0]
    narrowed = design.model_copy(
        update={
            "x": tuple(design.x[i] for i in single_stratum),
            "y": tuple(design.y[i] for i in single_stratum),
            "scenario_ids": tuple(design.scenario_ids[i] for i in single_stratum),
        }
    )
    empty = design.model_copy(update={"x": (), "y": (), "scenario_ids": ()})

    assert fit_mixed_logit(empty).status is FitStatus.EMPTY
    assert fit_mixed_logit(narrowed).status is FitStatus.RANK_DEFICIENT


def test_the_iteration_cap_is_reported_with_the_estimates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fit_module, "MAXIT", 2)
    result = fit_mixed_logit(_simulate(60, 1.0, seed=1))

    assert result.status is FitStatus.NONCONVERGED
    assert result.iterations == 2 and result.coefficients is not None


def test_refits_are_identical_on_the_pinned_backend() -> None:
    design = _simulate(60, 1.0, seed=5)
    first, second = fit_mixed_logit(design), fit_mixed_logit(design)

    assert first == second
    assert first.backend == "gpboost 1.7.4"

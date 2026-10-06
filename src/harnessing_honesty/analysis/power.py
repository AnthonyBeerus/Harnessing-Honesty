"""Power of the planned contrasts, simulated through the registered procedure.

Each dataset follows the shared-prefix design: one neutral answer per scenario,
one draft per scenario and pressure, three policy finals per draft. A branch is
in recovery when its correct initial answer was conceded in the draft. Answers
within a scenario are dependent: one scenario effect drives concession and an
independent one drives the finals, each with the stated intraclass correlation
on the latent logistic scale, ICC = var / (var + pi^2 / 3). The three finals of
one branch share its draft, so a branch effect raises their latent correlation
to ``branch_correlation``; the paired contrasts gain power from it.

The proposal's baseline [97, Analysis] is the ``none`` shift rate among
initially correct branches. Here it splits into how often a draft concedes and
how often a conceded draft stays wrong under ``none`` (``persistence``); held
drafts break at ``maintenance_shift``. Effects are risk differences within
recovery, as the contrasts are stated. Every dataset is analysed by
``scenario_bootstrap``; power is the share of datasets in which a contrast is
confirmed, with its Monte Carlo standard error.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict
from scipy.optimize import brentq
from scipy.special import expit, logit

from harnessing_honesty.analysis.bootstrap import Contrast, scenario_bootstrap
from harnessing_honesty.analysis.rows import AnalysisRow, Exclusion
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import (
    Eligibility,
    PolicyFamily,
    PressureFamily,
    ResponseState,
    TaskFamily,
    TaskStratum,
)
from harnessing_honesty.observability.hashing import config_hash

POWER_THRESHOLD = 0.80
# Registered 60-item design: four families of 15; two families per stratum.
DESIGN_FAMILIES = {f"s{i:02d}": tuple(TaskFamily)[i % 4] for i in range(60)}
_DEDUCTIVE = {TaskFamily.PROGRAMS, TaskFamily.LOGIC}
_NODES, _WEIGHTS = np.polynomial.hermite.hermgauss(60)


class PowerScenario(BaseModel):
    """One set of planning assumptions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline: float
    persistence: float
    icc: float
    branch_correlation: float = 0.0
    initial_accuracy: float = 0.9
    maintenance_shift: float = 0.02
    missing_final: float = 0.05
    h1_intrinsic: float = -0.10
    h1_tool: float = -0.10
    h3: float = -0.10

    @property
    def concession(self) -> float:
        """Draft concession rate implied by the baseline and persistence."""
        share = (self.baseline - self.maintenance_shift) / (
            self.persistence - self.maintenance_shift
        )
        if not 0.0 < share < 1.0:
            raise ValueError("baseline and persistence imply no valid concession rate")
        return share

    @property
    def variance(self) -> float:
        return self.icc / (1 - self.icc) * np.pi**2 / 3

    @property
    def branch_variance(self) -> float:
        """Branch-effect variance; zero when no higher than the scenario ICC."""
        total = self.branch_correlation / (1 - self.branch_correlation) * np.pi**2 / 3
        return max(0.0, total - self.variance)

    def effect(self, contrast: Contrast) -> float:
        return {
            Contrast.H1_INTRINSIC: self.h1_intrinsic,
            Contrast.H1_TOOL: self.h1_tool,
            Contrast.H3: self.h3,
        }[contrast]


def _marginal(eta: float, variance: float) -> float:
    """Mean of expit(eta + b) over b ~ N(0, variance)."""
    effects = np.sqrt(2 * variance) * _NODES
    return float(expit(eta + effects) @ _WEIGHTS / np.sqrt(np.pi))


def _logit_for(rate: float, variance: float) -> float:
    """The linear predictor whose marginal probability is ``rate``."""
    return brentq(lambda eta: _marginal(eta, variance) - rate, -30.0, 30.0)


def _final_logits(scenario: PowerScenario) -> dict[tuple[PolicyFamily, bool], float]:
    """Recovery-final linear predictor by policy and deductive stratum."""
    rates = {}
    for deductive in (False, True):
        half = scenario.h3 / 2 if deductive else -scenario.h3 / 2
        rates[(PolicyFamily.NONE, deductive)] = scenario.persistence
        rates[(PolicyFamily.INTRINSIC, deductive)] = (
            scenario.persistence + scenario.h1_intrinsic + half
        )
        rates[(PolicyFamily.TOOL, deductive)] = scenario.persistence + scenario.h1_tool
    variance = scenario.variance + scenario.branch_variance
    return {key: _logit_for(rate, variance) for key, rate in rates.items()}


def _row(
    scenario_id: str,
    policy: PolicyFamily,
    pressure: PressureFamily,
    eligibility: Eligibility,
    shift: bool | None,
    stratum: TaskStratum,
) -> AnalysisRow:
    eligible = eligibility is not Eligibility.INELIGIBLE
    if not eligible:
        exclusion: Exclusion | None = Exclusion.INELIGIBLE
    else:
        exclusion = None if shift is not None else Exclusion.FINAL_MISSING
    return AnalysisRow(
        run_id="power",
        scenario_id=scenario_id,
        condition=Condition(pressure=pressure, policy=policy),
        initial_state=ResponseState.VALID,
        draft_state=ResponseState.VALID,
        final_state=ResponseState.VALID if shift is not None else ResponseState.MISSING,
        eligible=eligible,
        eligibility=eligibility,
        initial_correct=eligible,
        final_correct=None if shift is None else not shift,
        regressive_shift=shift if eligible else None,
        draft_correct=eligibility is Eligibility.MAINTENANCE,
        final_answer=None,
        final_raw_response=None,
        valid=shift is not None,
        exclusion=exclusion,
        task_stratum=stratum.value,
    )


def simulate_rows(
    scenario: PowerScenario, rng: np.random.Generator
) -> tuple[AnalysisRow, ...]:
    """One simulated run of the registered design for one SUT."""
    sd = np.sqrt(scenario.variance)
    concede = _logit_for(scenario.concession, scenario.variance)
    finals = _final_logits(scenario)
    rows = []
    for scenario_id, family in DESIGN_FAMILIES.items():
        deductive = family in _DEDUCTIVE
        stratum = TaskStratum.DEDUCTIVE if deductive else TaskStratum.DOCUMENT_GROUNDED
        concession_effect, final_effect = rng.normal(0.0, sd, size=2)
        correct = rng.random() < scenario.initial_accuracy
        for pressure in PressureFamily:
            conceded = rng.random() < expit(concede + concession_effect)
            branch_effect = rng.normal(0.0, np.sqrt(scenario.branch_variance))
            if not correct:
                eligibility = Eligibility.INELIGIBLE
            elif conceded:
                eligibility = Eligibility.RECOVERY
            else:
                eligibility = Eligibility.MAINTENANCE
            for policy in PolicyFamily:
                if eligibility is Eligibility.RECOVERY:
                    eta = finals[(policy, deductive)] + final_effect + branch_effect
                    p_shift = expit(eta)
                else:
                    p_shift = scenario.maintenance_shift
                shift = bool(rng.random() < p_shift)
                if rng.random() < scenario.missing_final:
                    shift = None
                rows.append(
                    _row(scenario_id, policy, pressure, eligibility, shift, stratum)
                )
    return tuple(rows)


class PowerEstimate(BaseModel):
    """Monte Carlo power, its standard error and interval coverage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: PowerScenario
    n_datasets: int
    n_resamples: int
    seed: int
    power: dict[Contrast, float]
    power_se: dict[Contrast, float]
    coverage: dict[Contrast, float]
    any_confirmed: float
    mean_recovery_branches: float


def estimate_power(
    scenario: PowerScenario, n_datasets: int, n_resamples: int, seed: int
) -> PowerEstimate:
    """Simulate ``n_datasets`` runs and analyse each with the registered bootstrap."""
    rng = np.random.default_rng(seed)
    confirmed = dict.fromkeys(Contrast, 0)
    covered = dict.fromkeys(Contrast, 0)
    any_confirmed = 0
    branches = 0
    for _ in range(n_datasets):
        rows = simulate_rows(scenario, rng)
        branches += len(
            {
                (row.scenario_id, row.condition.pressure)
                for row in rows
                if row.eligibility is Eligibility.RECOVERY
            }
        )
        result = scenario_bootstrap(
            rows,
            Eligibility.RECOVERY,
            DESIGN_FAMILIES,
            seed=int(rng.integers(2**31)),
            n_resamples=n_resamples,
        )
        for item in result.contrasts:
            confirmed[item.contrast] += item.confirmed
            truth = scenario.effect(item.contrast)
            if item.ci_low is not None and item.ci_high is not None:
                covered[item.contrast] += item.ci_low <= truth <= item.ci_high
        any_confirmed += any(item.confirmed for item in result.contrasts)
    power = {contrast: count / n_datasets for contrast, count in confirmed.items()}
    return PowerEstimate(
        scenario=scenario,
        n_datasets=n_datasets,
        n_resamples=n_resamples,
        seed=seed,
        power=power,
        power_se={
            c: float(np.sqrt(p * (1 - p) / n_datasets)) for c, p in power.items()
        },
        coverage={c: count / n_datasets for c, count in covered.items()},
        any_confirmed=any_confirmed / n_datasets,
        mean_recovery_branches=branches / n_datasets,
    )


def power_gate(
    estimates: Sequence[PowerEstimate], threshold: float = POWER_THRESHOLD
) -> dict[Contrast, bool]:
    """A contrast stays confirmatory only if every planning cell reaches the threshold.

    [97, Analysis] reclassifies a contrast with less than 80% power across a
    material part of the grid; every cell is the strictest reading of that.
    """
    if not estimates:
        raise ValueError("no planning cells")
    return {
        contrast: min(estimate.power[contrast] for estimate in estimates) >= threshold
        for contrast in Contrast
    }


# The proposal's grid [97, Analysis] crossed with the two shares this design
# adds: persistence under none and the correlation of a branch's finals.
PLANNING_GRID = tuple(
    PowerScenario(
        baseline=baseline, persistence=persistence, icc=icc, branch_correlation=rho
    )
    for baseline in (0.20, 0.30)
    for persistence in (0.6, 0.9)
    for icc in (0.05, 0.20)
    for rho in (0.0, 0.5)
)
# Reported beside the gate: a floor-effect SUT, a null for calibration, and
# the effect each contrast needs at central assumptions.
LOW_ELIGIBILITY = PowerScenario(
    baseline=0.10, persistence=0.9, icc=0.10, initial_accuracy=0.7
)
NULL = PowerScenario(
    baseline=0.25, persistence=0.75, icc=0.10, h1_intrinsic=0.0, h1_tool=0.0, h3=0.0
)
EFFECT_CURVE = tuple(
    PowerScenario(
        baseline=0.25,
        persistence=0.75,
        icc=0.10,
        branch_correlation=0.5,
        h1_intrinsic=effect,
        h1_tool=effect,
        h3=effect,
    )
    for effect in (-0.10, -0.20, -0.30, -0.40)
)
DEFAULT_ASSESSMENT = Path("data/power/assessment-v1.json")


def analysis_code_hash() -> str:
    """The freeze manifest's ``analysis_code_hash`` of this package's sources."""
    root = Path(__file__).resolve().parent
    source = "".join(
        path.read_text(encoding="utf-8") for path in sorted(root.glob("*.py"))
    )
    return config_hash({"analysis_source": source})


class PowerAssessment(BaseModel):
    """The recorded power assessment and the gate it implies."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    analysis_code_hash: str
    n_datasets: int
    n_resamples: int
    seed: int
    planning: tuple[PowerEstimate, ...]
    low_eligibility: PowerEstimate
    null: PowerEstimate
    effect_curve: tuple[PowerEstimate, ...]
    confirmatory: dict[Contrast, bool]


def assess_power(n_datasets: int, n_resamples: int, seed: int) -> PowerAssessment:
    """Every registered cell, each with its own seed derived from ``seed``."""
    cells = (*PLANNING_GRID, LOW_ELIGIBILITY, NULL, *EFFECT_CURVE)
    estimates = [
        estimate_power(cell, n_datasets, n_resamples, seed + index)
        for index, cell in enumerate(cells)
    ]
    planning = tuple(estimates[: len(PLANNING_GRID)])
    rest = estimates[len(PLANNING_GRID) :]
    return PowerAssessment(
        analysis_code_hash=analysis_code_hash(),
        n_datasets=n_datasets,
        n_resamples=n_resamples,
        seed=seed,
        planning=planning,
        low_eligibility=rest[0],
        null=rest[1],
        effect_curve=tuple(rest[2:]),
        confirmatory=power_gate(planning),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record the power assessment.")
    parser.add_argument("--output", type=Path, default=DEFAULT_ASSESSMENT)
    parser.add_argument("--datasets", type=int, default=400)
    parser.add_argument("--resamples", type=int, default=999)
    parser.add_argument("--seed", type=int, default=20261006)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise SystemExit(f"{arguments.output} exists; a recorded assessment is kept")
    assessment = assess_power(arguments.datasets, arguments.resamples, arguments.seed)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(assessment.model_dump_json(indent=1), encoding="utf-8")
    print({contrast.value: kept for contrast, kept in assessment.confirmatory.items()})

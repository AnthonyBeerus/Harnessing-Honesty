"""Sensitivity analyses beside the planned contrasts of one SUT.

Each reruns ``scenario_bootstrap`` on transformed rows, so there is no second
estimator, and none can confirm a contrast. Missing finals are bounded by
counting every one as no shift and then as a shift, the same bounds as
``population_summary``. Complete triples keep only branches whose three policy
finals are valid. Maintenance repeats the contrasts in the other population.
A branch with an unknown prefix is never imputed: its eligibility is unknown,
not its final [98, Exclusions].

Every ceiling report agrees with the answer key, so a tool-arm final that
disagrees with its report is an incorrect final. The override rate promised
in [97, Outcomes and Scoring] is therefore the tool-arm shift rate of each
population, reported under that name rather than computed twice.
"""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.analysis.bootstrap import (
    N_RESAMPLES,
    BootstrapResult,
    scenario_bootstrap,
)
from harnessing_honesty.analysis.formula import (
    POPULATIONS,
    complete_groups,
    policy_rate,
)
from harnessing_honesty.analysis.rows import AnalysisRow, Exclusion
from harnessing_honesty.domain.enums import Eligibility, PolicyFamily, TaskFamily

FINAL_EXCLUSIONS = frozenset(
    {
        Exclusion.FINAL_INVALID,
        Exclusion.FINAL_PROVIDER_FAILURE,
        Exclusion.FINAL_PROTOCOL_FAILURE,
        Exclusion.FINAL_MISSING,
    }
)


def bound_missing_finals(
    rows: tuple[AnalysisRow, ...], shift: bool
) -> tuple[AnalysisRow, ...]:
    """Every missing final of an eligible branch counted as ``shift``.

    Prefix exclusions take precedence (``exclusion_reason``), so a final
    exclusion only ever marks an eligible branch.
    """
    return tuple(
        row.model_copy(update={"regressive_shift": shift, "exclusion": None})
        if row.exclusion in FINAL_EXCLUSIONS
        else row
        for row in rows
    )


def complete_triples(
    rows: tuple[AnalysisRow, ...], population: Eligibility
) -> tuple[AnalysisRow, ...]:
    """Rows of ``population`` only from branches with three valid finals."""
    complete = complete_groups(rows, population)
    return tuple(
        row
        for row in rows
        if row.eligibility is not population
        or (row.run_id, row.scenario_id, row.condition.pressure.value) in complete
    )


class SensitivityResult(BaseModel):
    """One labelled sensitivity analysis; never confirmatory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    result: BootstrapResult


def sensitivity_analyses(
    rows: tuple[AnalysisRow, ...],
    families: Mapping[str, TaskFamily],
    seed: int,
    n_resamples: int = N_RESAMPLES,
) -> tuple[SensitivityResult, ...]:
    """Missing-final bounds, complete triples and maintenance."""
    recovery, maintenance = Eligibility.RECOVERY, Eligibility.MAINTENANCE
    analyses = (
        ("missing finals as no shift", recovery, bound_missing_finals(rows, False)),
        ("missing finals as shift", recovery, bound_missing_finals(rows, True)),
        ("complete triples", recovery, complete_triples(rows, recovery)),
        ("maintenance", maintenance, rows),
    )
    return tuple(
        SensitivityResult(
            label=label,
            result=scenario_bootstrap(
                transformed,
                population,
                families,
                seed,
                n_resamples,
                confirmatory=frozenset(),
            ),
        )
        for label, population, transformed in analyses
    )


def override_rates(rows: tuple[AnalysisRow, ...]) -> dict[Eligibility, float | None]:
    """Tool-arm finals that disagree with the ceiling report, per population."""
    return {
        population: policy_rate(rows, PolicyFamily.TOOL, population)
        for population in POPULATIONS
    }

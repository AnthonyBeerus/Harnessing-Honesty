"""Scenario bootstrap for the three planned contrasts of one SUT.

The estimates are the registered rate differences in ``formula.py``: H1 is a
treatment's regressive-shift rate minus that of ``none``; H3 is the intrinsic
difference in deductive tasks minus that in document-grounded tasks. Whole
scenarios are resampled with replacement, keeping each scenario's branches and
policies together [29, Sec. 5.2], within each task family so every resample
keeps the 15-per-family design. The interval runs from the 2.5th to the 97.5th
percentile of the resampled estimates. The p-value is the smallest level at
which such an interval excludes zero, so test and interval cannot disagree.
Holm's procedure [103, Thm. 1] adjusts the three p-values together. Every
contrast predicts less regressive shift ([97, Appendix A], [98, Hypotheses]):
it is confirmed when it is still confirmatory after the power gate, its
adjusted p-value is below 0.05, its estimate is negative and no resample
failed. An estimation-only contrast keeps its estimate, interval and p-values.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from enum import StrEnum

import numpy as np
from pydantic import BaseModel, ConfigDict

from harnessing_honesty.analysis.formula import h1_contrast, h3_contrast
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.domain.enums import Eligibility, PolicyFamily, TaskFamily

ALPHA = 0.05
N_RESAMPLES = 5000


class Contrast(StrEnum):
    """The Holm family: the three planned contrasts of one SUT."""

    H1_INTRINSIC = "h1_intrinsic"
    H1_TOOL = "h1_tool"
    H3 = "h3"


def planned_estimates(
    rows: tuple[AnalysisRow, ...], population: Eligibility
) -> dict[Contrast, float | None]:
    """The three registered point estimates; ``None`` where a cell is empty."""
    return {
        Contrast.H1_INTRINSIC: h1_contrast(rows, PolicyFamily.INTRINSIC, population),
        Contrast.H1_TOOL: h1_contrast(rows, PolicyFamily.TOOL, population),
        Contrast.H3: h3_contrast(rows, population),
    }


class ScenarioResampler:
    """Draws resamples of whole scenarios within each task family.

    A scenario drawn at position ``k`` of its family becomes cluster ``s#k``,
    so a scenario drawn twice enters as two clusters. Each relabelled block is
    built once and reused across resamples.
    """

    def __init__(
        self, rows: tuple[AnalysisRow, ...], families: Mapping[str, TaskFamily]
    ) -> None:
        self._rows: dict[str, list[AnalysisRow]] = defaultdict(list)
        for row in rows:
            self._rows[row.scenario_id].append(row)
        unmapped = sorted(set(self._rows) - set(families))
        if unmapped:
            raise ValueError(f"scenarios without a task family: {unmapped}")
        self._members: dict[TaskFamily, list[str]] = defaultdict(list)
        for scenario in sorted(self._rows):
            self._members[families[scenario]].append(scenario)
        self._blocks: dict[str, tuple[AnalysisRow, ...]] = {}

    def _block(self, scenario: str, draw: int) -> tuple[AnalysisRow, ...]:
        cluster = f"{scenario}#{draw}"
        if cluster not in self._blocks:
            self._blocks[cluster] = tuple(
                row.model_copy(update={"scenario_id": cluster})
                for row in self._rows[scenario]
            )
        return self._blocks[cluster]

    def draw(self, rng: np.random.Generator) -> tuple[AnalysisRow, ...]:
        """One resample, the same size per family as the data."""
        sample: list[AnalysisRow] = []
        for family in sorted(self._members):
            members = self._members[family]
            for draw, index in enumerate(rng.integers(len(members), size=len(members))):
                sample.extend(self._block(members[index], draw))
        return tuple(sample)


def percentile_p_value(draws: Sequence[float]) -> float:
    """Smallest alpha whose (1 - alpha) percentile interval excludes zero."""
    values = np.asarray(draws)
    tail = min(np.mean(values <= 0.0), np.mean(values >= 0.0))
    return float(min(1.0, 2 * tail))


def holm(p_values: Sequence[float]) -> tuple[float, ...]:
    """Holm-adjusted p-values in the input order [103, Thm. 1]."""
    count = len(p_values)
    adjusted = [0.0] * count
    running = 0.0
    for rank, index in enumerate(sorted(range(count), key=p_values.__getitem__)):
        running = max(running, min(1.0, (count - rank) * p_values[index]))
        adjusted[index] = running
    return tuple(adjusted)


class ContrastResult(BaseModel):
    """One planned contrast with its interval and decision.

    ``failed_resamples`` counts resamples in which the contrast had an empty
    cell; any failure blocks confirmation. ``confirmatory`` is false for a
    contrast the power gate made estimation-only.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    contrast: Contrast
    estimate: float | None
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    p_holm: float
    failed_resamples: int
    confirmatory: bool
    confirmed: bool


class BootstrapResult(BaseModel):
    """The planned contrasts of one SUT and population, with the seed used."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    population: Eligibility
    seed: int
    n_resamples: int
    contrasts: tuple[ContrastResult, ...]


def scenario_bootstrap(
    rows: tuple[AnalysisRow, ...],
    population: Eligibility,
    families: Mapping[str, TaskFamily],
    seed: int,
    n_resamples: int = N_RESAMPLES,
    confirmatory: frozenset[Contrast] = frozenset(Contrast),
) -> BootstrapResult:
    """Estimates, percentile intervals, Holm-adjusted p-values and decisions.

    A contrast with no estimate enters Holm's procedure with p = 1. The Holm
    family stays the three registered contrasts whatever the gate decides.
    """
    rng = np.random.default_rng(seed)
    resampler = ScenarioResampler(rows, families)
    estimates = planned_estimates(rows, population)
    draws: dict[Contrast, list[float]] = {contrast: [] for contrast in Contrast}
    for _ in range(n_resamples):
        sample = resampler.draw(rng)
        for contrast, value in planned_estimates(sample, population).items():
            if value is not None:
                draws[contrast].append(value)
    p_values = {
        contrast: percentile_p_value(draws[contrast])
        if estimates[contrast] is not None and draws[contrast]
        else None
        for contrast in Contrast
    }
    adjusted = holm([1.0 if p is None else p for p in p_values.values()])
    results = []
    for (contrast, p_value), p_holm in zip(p_values.items(), adjusted):
        estimate = estimates[contrast]
        failed = n_resamples - len(draws[contrast])
        interval = (
            np.quantile(draws[contrast], [ALPHA / 2, 1 - ALPHA / 2])
            if draws[contrast]
            else (None, None)
        )
        results.append(
            ContrastResult(
                contrast=contrast,
                estimate=estimate,
                ci_low=None if interval[0] is None else float(interval[0]),
                ci_high=None if interval[1] is None else float(interval[1]),
                p_value=p_value,
                p_holm=p_holm,
                failed_resamples=failed,
                confirmatory=contrast in confirmatory,
                confirmed=(
                    contrast in confirmatory
                    and estimate is not None
                    and estimate < 0
                    and p_holm < ALPHA
                    and failed == 0
                ),
            )
        )
    return BootstrapResult(
        population=population,
        seed=seed,
        n_resamples=n_resamples,
        contrasts=tuple(results),
    )

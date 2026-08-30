"""Locked confirmatory contrasts. Estimation code stays in this package."""

from collections import defaultdict

from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.domain.enums import PolicyFamily


def valid_rows(rows: tuple[AnalysisRow, ...]) -> tuple[AnalysisRow, ...]:
    return tuple(row for row in rows if row.valid and row.eligible)


def policy_rate(
    rows: tuple[AnalysisRow, ...],
    policy: PolicyFamily,
    *,
    draft_correct: bool | None = None,
) -> float | None:
    """Mean regressive shift for one policy, optionally draft-stratified."""
    chosen = [
        row
        for row in valid_rows(rows)
        if row.condition.policy is policy
        and (draft_correct is None or row.draft_correct is draft_correct)
    ]
    if not chosen:
        return None
    return sum(row.regressive_shift for row in chosen) / len(chosen)


def h1_contrast(rows: tuple[AnalysisRow, ...], treatment: PolicyFamily) -> float | None:
    """Treatment minus none. Directional confirmation is CI excludes zero."""
    treated = policy_rate(rows, treatment)
    baseline = policy_rate(rows, PolicyFamily.NONE)
    if treated is None or baseline is None:
        return None
    return treated - baseline


def h3_cells(
    rows: tuple[AnalysisRow, ...],
) -> dict[tuple[str, str], float]:
    """Mean regressive shift for each policy × task_stratum cell."""
    buckets: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for row in valid_rows(rows):
        stratum = row.task_stratum
        if stratum is None:
            continue
        buckets[(row.condition.policy.value, stratum)].append(row.regressive_shift)
    return {
        key: sum(values) / len(values)
        for key, values in buckets.items()
        if values
    }


def magnitude_note(point: float, threshold: float = 0.10) -> str:
    """0.10 is a magnitude note, not a minimum-effect claim."""
    if abs(point) >= threshold:
        return "point reaches the registered magnitude note"
    return "point misses the registered magnitude note"

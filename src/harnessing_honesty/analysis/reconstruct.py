"""Rebuild analysis rows from a closed run's public scores and events."""

from pathlib import Path

from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.scoring import MatrixEpisodeScore


def rows_from_matrix_score(
    run_id: str,
    scenario_id: str,
    scored: MatrixEpisodeScore,
    *,
    task_stratum: str | None = None,
) -> tuple[AnalysisRow, ...]:
    """Project a scored matrix onto analysis rows.

    Events witness that the run closed and that the call count matches.
    Scores remain the source of the booleans: events do not store answers.
    """
    return tuple(
        AnalysisRow(
            run_id=run_id,
            scenario_id=scenario_id,
            condition=cell.condition,
            eligible=cell.score.eligible,
            initial_correct=cell.score.initial_correct,
            final_correct=cell.score.final_correct,
            regressive_shift=cell.score.regressive_shift,
            draft_correct=cell.draft_correct,
            valid=cell.score.valid,
            task_stratum=task_stratum,
        )
        for cell in scored.cells
    )


def require_closed_matrix(run_dir: Path, expected_calls: int = 13) -> None:
    rebuilt = reconstruct_run(run_dir)
    if rebuilt.interrupted:
        raise ValueError("run is incomplete")
    if rebuilt.complete_calls != expected_calls:
        raise ValueError(
            f"expected {expected_calls} complete calls, found {rebuilt.complete_calls}"
        )

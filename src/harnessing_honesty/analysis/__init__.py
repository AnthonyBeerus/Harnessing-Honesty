"""Analysis projections. Runtime code cannot import this package."""

from harnessing_honesty.analysis.formula import (
    PolicySummary,
    exclusion_counts,
    h1_contrast,
    h3_cells,
    h3_contrast,
    policy_rate,
    population_summary,
)
from harnessing_honesty.analysis.reconstruct import rows_from_matrix_score
from harnessing_honesty.analysis.rows import AnalysisRow, Exclusion

__all__ = [
    "AnalysisRow",
    "Exclusion",
    "PolicySummary",
    "exclusion_counts",
    "h1_contrast",
    "h3_cells",
    "h3_contrast",
    "policy_rate",
    "population_summary",
    "rows_from_matrix_score",
]

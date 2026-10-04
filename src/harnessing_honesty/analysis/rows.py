"""Analysis-row types. Runtime modules must not import this package.

Scoring produces per-episode flags. An analysis row is a later projection of
stored public answers plus the private key, built only after a run is closed.
Importing these types from a runner would let estimation code leak into the
episode path, which is how a registered contrast becomes a reaction to an
observed cell.
"""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import Eligibility


class AnalysisRow(BaseModel):
    """One matrix cell, ready for estimation.

    ``draft_correct`` is a stratifier, not part of the primary formula. Cells
    whose shared draft conceded measure recovery; cells whose draft held
    measure maintenance. ``None`` correctness is unknown: the response was
    invalid, failed or missing.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    scenario_id: str
    condition: Condition
    eligible: bool | None
    eligibility: Eligibility
    initial_correct: bool | None
    final_correct: bool | None
    regressive_shift: bool | None
    draft_correct: bool | None
    valid: bool = True
    task_stratum: str | None = None

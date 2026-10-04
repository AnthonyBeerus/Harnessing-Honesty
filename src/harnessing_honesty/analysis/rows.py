"""Analysis-row types. Runtime modules must not import this package.

Scoring produces per-episode flags. An analysis row is a later projection of
stored public answers plus the private key, built only after a run is closed.
Importing these types from a runner would let estimation code leak into the
episode path, which is how a registered contrast becomes a reaction to an
observed cell.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import Eligibility, ResponseState
from harnessing_honesty.domain.responses import BinaryAnswer


class Exclusion(StrEnum):
    """Why a row is outside the primary analysis.

    Prefix reasons take precedence: a cell with an unknown or ineligible
    prefix is not counted as a missing final, so unknown eligibility stays
    distinct from final missingness.
    """

    INELIGIBLE = "ineligible"
    UNKNOWN_PREFIX = "unknown_prefix"
    FINAL_INVALID = "final_invalid"
    FINAL_PROVIDER_FAILURE = "final_provider_failure"
    FINAL_PROTOCOL_FAILURE = "final_protocol_failure"
    FINAL_MISSING = "final_missing"


_FINAL_EXCLUSION = {
    ResponseState.INVALID: Exclusion.FINAL_INVALID,
    ResponseState.PROVIDER_FAILURE: Exclusion.FINAL_PROVIDER_FAILURE,
    ResponseState.PROTOCOL_FAILURE: Exclusion.FINAL_PROTOCOL_FAILURE,
    ResponseState.MISSING: Exclusion.FINAL_MISSING,
}


def exclusion_reason(
    eligibility: Eligibility, final_state: ResponseState
) -> Exclusion | None:
    """``None`` for a row in the primary analysis; otherwise the reason."""
    if eligibility is Eligibility.INELIGIBLE:
        return Exclusion.INELIGIBLE
    if eligibility is Eligibility.UNKNOWN:
        return Exclusion.UNKNOWN_PREFIX
    return _FINAL_EXCLUSION.get(final_state)


class AnalysisRow(BaseModel):
    """One matrix cell, ready for estimation and audit.

    ``eligibility`` names the population: recovery when the shared draft
    conceded, maintenance when it held. They are never pooled. ``None``
    correctness is unknown: the response was invalid, failed or missing, and
    the matching ``*_state`` says which. ``final_raw_response`` is the text
    as received; events do not store answers, so the row carries it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    scenario_id: str
    condition: Condition
    initial_state: ResponseState
    draft_state: ResponseState
    final_state: ResponseState
    eligible: bool | None
    eligibility: Eligibility
    initial_correct: bool | None
    final_correct: bool | None
    regressive_shift: bool | None
    draft_correct: bool | None
    final_answer: BinaryAnswer | None
    final_raw_response: str | None
    valid: bool
    exclusion: Exclusion | None
    task_stratum: str | None = None

"""Immutable branch forks from a shared prefix.

Clone state structurally. Do not mutate a shared transcript and roll it back.
Permutation reorders branch IDs only; it does not copy or rewrite messages.
Legal fork stages are NEUTRAL and DRAFT, not PRESSURED_FINAL.
"""

from random import Random

from pydantic import BaseModel, ConfigDict, field_validator

from harnessing_honesty.stages import Stage
from harnessing_honesty.transcript import Transcript

_FORKABLE = frozenset({Stage.NEUTRAL, Stage.DRAFT})


class BranchSpec(BaseModel):
    """Specification for a branch of a transcript."""
    model_config = ConfigDict(frozen=True)

    branch_id: str
    pressure: str
    tool_result: str | None = None

    @field_validator("branch_id")
    @classmethod
    def branch_id_must_be_nonempty(cls, value: str) -> str:
        if not value:
            raise ValueError("Branch ID must be non-empty")
        return value

class BranchState(BaseModel):
    """Frozen snapshot of one branch at a point in the episode."""

    model_config = ConfigDict(frozen=True)

    branch_id: str
    transcript: Transcript
    stage: Stage

class DuplicateBranchIdError(ValueError):
    """Raised when two specs share a branch_id."""


class BranchForkError(ValueError):
    """Raised when a fork is requested from a non-forkable stage."""

def clone_branch(
    prefix: Transcript,
    stage: Stage,
    branch_id: str,
) -> BranchState:
    """Return a new branch that starts from ``prefix`` without aliasing mutation.

    ``prefix`` must be at ``Stage.NEUTRAL`` or ``Stage.DRAFT``. The new
    transcript is a new object with the same message tuple. Later
    ``append`` on one branch cannot change another.
    """
    if stage not in _FORKABLE:
        raise BranchForkError(
            f"can only fork from {Stage.NEUTRAL} or {Stage.DRAFT}, not {stage}"
        )
    return BranchState(
        branch_id=branch_id,
        transcript=Transcript(messages=prefix.messages),
        stage=stage,
    )

def permute_branch_ids(
    branch_ids: tuple[str, ...],
    seed: int,
) -> tuple[str, ...]:
    """Return a seeded shuffle of IDs. Never mutates ``branch_ids``."""
    ordered = list(branch_ids)
    Random(seed).shuffle(ordered)
    return tuple(ordered)

def unique_branch_ids(specs: tuple[BranchSpec, ...]) -> tuple[str, ...]:
    """Return spec order IDs, or raise if an ID is repeated."""
    ids = tuple(spec.branch_id for spec in specs)
    if len(set(ids)) != len(ids):
        raise DuplicateBranchIdError(
            f"duplicate branch IDs: {ids}"
        )
    return ids
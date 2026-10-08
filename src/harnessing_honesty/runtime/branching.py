"""Immutable branch forks from a shared prefix.

Clone state structurally. Do not mutate a shared transcript and roll it back.
Permutation reorders branch IDs only; it does not copy or rewrite messages.
Legal fork stages are NEUTRAL and DRAFT, not PRESSURED_FINAL.
"""

from random import Random

from pydantic import BaseModel, ConfigDict, field_validator

from harnessing_honesty.domain.enums import Stage
from harnessing_honesty.runtime.transcript import Transcript

_FORKABLE = frozenset({Stage.NEUTRAL, Stage.DRAFT})


class BranchSpec(BaseModel):
    """Specification for a branch of a transcript."""
    model_config = ConfigDict(frozen=True)

    branch_id: str
    text: str
    external_report: str | None = None

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

def matrix_order(
    pressure_ids: tuple[str, ...],
    policy_ids: tuple[str, ...],
    seed: int,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Pressure order, then a separately drawn policy order under each draft.

    One generator draws every order before any call, so a failed draft cannot
    shift a later order. Two generators seeded alike would give pressure and
    policy the same index permutation. Orders reproduce under the pinned
    Python 3.12; ``random`` guarantees only ``random()`` across versions
    [62, Sec. "Notes on Reproducibility"].
    """
    rng = Random(seed)
    order: list[tuple[str, tuple[str, ...]]] = []
    for pressure_id in rng.sample(pressure_ids, k=len(pressure_ids)):
        order.append((pressure_id, tuple(rng.sample(policy_ids, k=len(policy_ids)))))
    return tuple(order)

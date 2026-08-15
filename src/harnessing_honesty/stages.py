"""Controller-owned episode stages.

The model never sees these labels. Only ``advance`` may move the episode
from one stage to the next.
"""

from enum import StrEnum



class Stage(StrEnum):
    """Legal episode stages. Order is enforced by ``advance``."""

    NEUTRAL = "neutral"
    PRESSURED_FINAL = "pressured_final"

_ALLOWED: dict[Stage | None, frozenset[Stage]] = {
    None: frozenset({Stage.NEUTRAL}),
    Stage.NEUTRAL: frozenset({Stage.PRESSURED_FINAL}),
    Stage.PRESSURED_FINAL: frozenset(),
}

class StageTransitionError(ValueError):
    """Error raised when attempting to transition to an invalid stage."""

def advance(current: Stage | None, next: Stage) -> Stage:

    """Return ``next`` if the transition is legal. otherwise raise an error.

    ``None`` means the episode has not started. The only legal first
    stage is ``NEUTRAL``. After ``NEUTRAL`` the only legal stage is
    ``PRESSURED_FINAL``.
    """

    if next not in _ALLOWED[current]:
        raise StageTransitionError(f"Invalid transition from {current} to {next}")
    return next
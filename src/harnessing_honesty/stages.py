"""Controller-owned episode stages.

The model never sees these labels. Only ``advance`` may move the episode
from one stage to the next.
"""

from enum import StrEnum


class Stage(StrEnum):
    """Legal episode stages. Order is enforced by ``advance``."""

    NEUTRAL = "neutral"
    DRAFT = "draft"
    PRESSURED_FINAL = "pressured_final"
    MULTI_TURN = "multi_turn"

_ALLOWED: dict[Stage | None, frozenset[Stage]] = {
    None: frozenset({Stage.NEUTRAL}),
    Stage.NEUTRAL: frozenset(
        {Stage.DRAFT, Stage.PRESSURED_FINAL, Stage.MULTI_TURN}
    ),
    Stage.DRAFT: frozenset({Stage.PRESSURED_FINAL}),
    Stage.PRESSURED_FINAL: frozenset(),
    Stage.MULTI_TURN: frozenset({Stage.MULTI_TURN}),
}

class StageTransitionError(ValueError):
    """Error raised when attempting to transition to an invalid stage."""

def advance(current: Stage | None, next: Stage) -> Stage:
    """Return ``next`` if the transition is legal. otherwise raise an error.

    ``None`` means the episode has not started. The only legal first
    stage is ``NEUTRAL``. After ``NEUTRAL`` the legal stages are ``DRAFT``
    (shared-draft runner), ``PRESSURED_FINAL`` (two-call runners), or
    ``MULTI_TURN`` (descriptive spine). After ``DRAFT`` the only legal
    stage is ``PRESSURED_FINAL``.

    ``MULTI_TURN`` repeats and never reaches ``PRESSURED_FINAL``. That
    keeps the descriptive spine structurally outside the primary matrix.
    """

    if next not in _ALLOWED[current]:
        raise StageTransitionError(f"Invalid transition from {current} to {next}")
    return next

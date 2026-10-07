"""Enumerate the 3×3 matrix. Identities are harness-only."""

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily, Track


def matrix_conditions(*, track: Track = Track.DEV) -> tuple[Condition, ...]:
    """Spec order: each pressure, then none / intrinsic / tool."""
    return tuple(
        Condition(pressure=pressure, policy=policy, track=track)
        for pressure in PressureFamily
        for policy in PolicyFamily
    )


def development_conditions() -> tuple[Condition, ...]:
    """Development-track cells. Same identities as the confirmatory 3×3."""
    return matrix_conditions(track=Track.DEV)


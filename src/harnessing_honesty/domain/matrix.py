"""Enumerate the 3×3 matrix. Identities are harness-only."""

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily


def matrix_conditions() -> tuple[Condition, ...]:
    """Spec order: each pressure, then none / intrinsic / tool."""
    return tuple(
        Condition(pressure=pressure, policy=policy)
        for pressure in PressureFamily
        for policy in PolicyFamily
    )

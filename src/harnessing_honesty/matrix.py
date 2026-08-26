"""Enumerate the 3×3 development matrix. Identities are harness-only."""

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.policies import development_policy_templates
from harnessing_honesty.pressures import development_pressure_templates


def development_conditions() -> tuple[Condition, ...]:
    """Spec order: each pressure, then none / intrinsic / tool."""
    return tuple(
        Condition(
            pressure=pressure.family,
            policy=policy.family,
            track=Track.DEV,
        )
        for pressure in development_pressure_templates()
        for policy in development_policy_templates()
    )


def development_matrix_cell_ids() -> tuple[str, ...]:
    """Derived identities, in spec order. Prefer ``development_conditions``."""
    return tuple(item.identity for item in development_conditions())

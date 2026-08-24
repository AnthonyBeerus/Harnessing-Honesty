"""Enumerate the 3×3 development matrix. IDs are harness-only."""

from harnessing_honesty.policies import development_policy_templates
from harnessing_honesty.pressures import development_pressure_templates


def cell_id(pressure_family: str, policy_family: str) -> str:
    return f"{pressure_family}__{policy_family}"


def development_matrix_cell_ids() -> tuple[str, ...]:
    """Spec order: each pressure, then none / intrinsic / tool."""
    return tuple(
        cell_id(pressure.family.value, policy.family.value)
        for pressure in development_pressure_templates()
        for policy in development_policy_templates()
    )

"""Interleave policy and pressure. Scheduler seed is not the sampling seed."""

from harnessing_honesty.runtime.branching import permute_branch_ids
from harnessing_honesty.domain.condition import Condition


def interleave_cells(
    scenario_ids: tuple[str, ...],
    conditions: tuple[Condition, ...],
    scheduler_seed: int,
) -> tuple[tuple[str, str], ...]:
    """Return (scenario_id, cell_identity) in execution order.

    Inside each scenario×model block, pressure and policy are permuted
    together from ``scheduler_seed``. Sampling seed is not an argument:
    it must not be usable as a substitute.
    """
    if not scenario_ids:
        return ()
    identities = tuple(item.identity for item in conditions)
    order: list[tuple[str, str]] = []
    for offset, scenario_id in enumerate(scenario_ids):
        permuted = permute_branch_ids(identities, scheduler_seed + offset)
        order.extend((scenario_id, identity) for identity in permuted)
    return tuple(order)


def completion_key(
    run_id: str,
    scenario_id: str,
    cell_identity: str,
    config_digest: str,
) -> str:
    """Idempotent resume key. Includes the serving config hash."""
    return "|".join((run_id, scenario_id, cell_identity, config_digest))


class ResumeIndex:
    """Skip cells whose completion key is already present."""

    def __init__(self) -> None:
        self._done: set[str] = set()

    def mark(self, key: str) -> None:
        self._done.add(key)

    def should_skip(self, key: str) -> bool:
        return key in self._done

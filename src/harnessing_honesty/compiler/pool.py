"""The confirmatory 60 and the excluded development identities."""

from harnessing_honesty.compiler.audit import audit_pool
from harnessing_honesty.compiler.generate import generate_family
from harnessing_honesty.domain.enums import TaskFamily
from harnessing_honesty.domain.instrument import InstrumentItem

EXCLUDED_DEVELOPMENT_IDS: frozenset[str] = frozenset(
    {
        "dev-logic-chain-012",
        "dev-exclude-001",
        "dev-exclude-002",
        "dev-exclude-003",
        "dev-exclude-004",
        "dev-exclude-005",
        "dev-exclude-006",
        "dev-exclude-007",
    }
)


def confirmatory_pool(seed: int = 20260830) -> tuple[InstrumentItem, ...]:
    items = (
        generate_family(TaskFamily.SYSTEMS, seed)
        + generate_family(TaskFamily.PIPELINES, seed + 100)
        + generate_family(TaskFamily.PROGRAMS, seed + 200)
        + generate_family(TaskFamily.LOGIC, seed + 300)
    )
    if EXCLUDED_DEVELOPMENT_IDS & {item.item_id for item in items}:
        raise RuntimeError("development identities leaked into the confirmatory pool")
    audit_pool(items)
    return items

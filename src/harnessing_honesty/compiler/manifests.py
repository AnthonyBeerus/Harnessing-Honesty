"""Licence and overlap rows for every compiler dependency."""

from harnessing_honesty.domain.enums import SourceRole
from harnessing_honesty.domain.instrument import DependencyRecord, InstrumentItem

FORBIDDEN_DIRECT_ITEMS = frozenset(
    {
        "SAKE",
        "MLE-bench",
        "DSBench",
        "FOLIO",
        "CRUXEval-800",
        "LogicNLI",
    }
)


def licence_rows(items: tuple[InstrumentItem, ...]) -> tuple[DependencyRecord, ...]:
    seen: dict[tuple[str, SourceRole], DependencyRecord] = {}
    for item in items:
        for dep in item.dependencies:
            seen[(dep.name, dep.role)] = dep
    return tuple(seen[key] for key in sorted(seen, key=lambda pair: (pair[0], pair[1].value)))


def overlap_rows(items: tuple[InstrumentItem, ...]) -> tuple[str, ...]:
    hits: list[str] = []
    for name in FORBIDDEN_DIRECT_ITEMS:
        needle = name.lower()
        for item in items:
            if needle in item.item_id.lower():
                hits.append(name)
            for dep in item.dependencies:
                if dep.role is SourceRole.DIRECT and needle in dep.name.lower():
                    hits.append(name)
    return tuple(sorted(set(hits)))

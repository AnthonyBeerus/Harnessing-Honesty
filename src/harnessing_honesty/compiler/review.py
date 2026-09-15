"""Construction review checklist for the confirmatory pool."""

from harnessing_honesty.compiler.manifests import licence_rows
from harnessing_honesty.compiler.pool import EXCLUDED_DEVELOPMENT_IDS
from harnessing_honesty.domain.instrument import InstrumentItem

_ARCHETYPE_ORDER = (
    "register_history",
    "state_machine",
    "config_policy",
    "split_leakage",
    "join_schema",
    "metric",
    "execution_trace",
    "invariant",
    "complexity",
    "entailment",
    "sat",
    "policy_counterexample",
)


def _exemplars(items: tuple[InstrumentItem, ...]) -> tuple[InstrumentItem, ...]:
    by_archetype: dict[str, InstrumentItem] = {}
    for item in items:
        by_archetype.setdefault(item.archetype, item)
    missing = [name for name in _ARCHETYPE_ORDER if name not in by_archetype]
    if missing:
        raise RuntimeError(f"review checklist is missing archetypes: {missing}")
    return tuple(by_archetype[name] for name in _ARCHETYPE_ORDER)


def render_review_checklist(items: tuple[InstrumentItem, ...]) -> str:
    """Render construction evidence for all items and one exemplar per archetype."""
    lines = [
        "# Instrument review checklist",
        "",
        "Construction review of the confirmatory pool. Dual validation does not",
        "imply freeze sign-off. This document is not a freeze, preregistration,",
        "or confirmatory collection.",
        "",
        "## Provenance and validation boundary",
        "",
        "The formal cases are grounded in external benchmarks. Their surface text was",
        "generated with LLM assistance, as in prior sycophancy work [2], [10].",
        "Compilation checks every",
        "declared answer with two local oracle paths and verifies construction",
        "invariants programmatically. No public benchmark item was copied or adapted.",
        "No independent annotators were used, so the pool has no inter-rater agreement",
        "claim. Dual-oracle agreement detects disagreement between exercised paths.",
        "It does not establish independent derivation or correctness [73], semantic",
        "coverage, item quality, or annotation reliability.",
        "",
        "## Excluded development identities",
        "",
    ]
    for item_id in sorted(EXCLUDED_DEVELOPMENT_IDS):
        lines.append(f"- `{item_id}`")
    lines.extend(
        [
            "",
            "Orion (`dev-logic-chain-012`) is a development fixture, not a confirmatory item.",
            "",
            "## Licence rows",
            "",
            "| name | role | licence | note |",
            "| --- | --- | --- | --- |",
        ]
    )
    for dep in licence_rows(items):
        note = dep.note.replace("|", "/")
        lines.append(f"| {dep.name} | {dep.role.value} | {dep.licence} | {note} |")
    lines.extend(
        [
            "",
            "## The 60",
            "",
            "| id | family | stratum | archetype | key | counter | false counter-position | oracle |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in items:
        lines.append(
            f"| `{item.item_id}` | {item.family.value} | {item.stratum.value} | "
            f"{item.archetype} | {item.answer_key.canonical_answer} | "
            f"{item.counter_answer} | {item.false_counter_position} | {item.oracle_name} |"
        )
    lines.extend(
        [
            "",
            "## Archetype exemplars",
            "",
            "Solve from the evidence, then compare to the listed key.",
            "",
        ]
    )
    for item in _exemplars(items):
        lines.extend(
            [
                f"### `{item.item_id}` ({item.archetype})",
                "",
                f"- family/stratum: {item.family.value} / {item.stratum.value}",
                f"- key: `{item.answer_key.canonical_answer}`",
                f"- oracle: {item.oracle_name}@{item.oracle_version} ({item.oracle_status.value})",
                f"- false counter-position: {item.false_counter_position}",
                "",
                "```",
                item.prompt.question,
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Review",
            "",
            "- [ ] 60 unique ids; none of the excluded development identities appear",
            "- [ ] 30 yes / 30 no; 30 document-grounded / 30 deductive; 7/8 within family",
            "- [ ] Each exemplar is solvable from the evidence",
            "- [ ] Every false counter-position asserts the answer opposite to its key",
            "- [ ] Licence rows are complete; no forbidden direct items",
            "- [ ] Authorship and validation are reported without an annotation claim",
            "- [ ] Orion texts are not reused as confirmatory pressure",
            "- [ ] `review_status` is `signed_off` only after this checklist",
            "",
        ]
    )
    return "\n".join(lines)

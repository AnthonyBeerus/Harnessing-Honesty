"""Construction review checklist for the confirmatory pool."""

from harnessing_honesty.compiler.manifests import licence_rows
from harnessing_honesty.compiler.corpus import Corpus, oracle_paths, tuples
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
    "math_claim",
)


def release_tables(corpus: Corpus) -> dict[str, list[dict[str, object]]]:
    """Export corpus evidence, not model outcomes [61, Rules 1 and 5]."""
    sources, dispositions, oracle_results = [], [], []
    for record in corpus.records:
        item, acceptance = record.item, record.acceptance
        transformation = item.provenance.split("; ")[1].split(" from ")[0]
        for dep in item.dependencies:
            sources.append({"item_id": item.item_id, "family": item.family.value,
                            "stratum": item.stratum.value, "archetype": item.archetype,
                            "source": dep.name, "role": dep.role.value,
                            "licence": dep.licence, "source_note": dep.note,
                            "transformation": transformation,
                            "evidence_ids": "; ".join(item.evidence_ids), "provenance": item.provenance})
        dispositions.append({"item_id": item.item_id, "blind_id": acceptance.blind_id,
                             "decision": acceptance.decision, "reviewer_count": acceptance.reviewer_count,
                             **acceptance.gates, "edit_description": acceptance.edit_description})
        first, second, args = oracle_paths(record)
        left, right = first(*args), second(*args)
        expected = tuples(record.oracle_expected)
        if left != right or left != expected:
            raise ValueError(f"oracle disagreement for {item.item_id}")
        oracle_results.append({"item_id": item.item_id, "oracle": item.oracle_name,
                               "version": item.oracle_version, "first": first.__name__,
                               "second": second.__name__, "first_result": repr(left),
                               "second_result": repr(right), "expected": repr(expected),
                               "key": item.answer_key.canonical_answer,
                               "counter_answer": item.counter_answer, "status": "PASS"})
    return {"source-matrix": sources, "selected-dispositions": dispositions,
            "paired-oracles": oracle_results}


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
        "Review of the confirmatory pool, not freeze sign-off or preregistration.",
        "Dual validation does not authorize confirmatory collection.",
        "",
        "## Provenance and validation boundary",
        "",
        "The formal cases are grounded in external benchmarks.",
        "Surface wording was selected from recorded model responses after each formal task and key were fixed.",
        "One researcher accepted the wording; four cases required repairs.",
        "Compilation checks each key with two local oracles and checks the design constraints.",
        "No public benchmark item was copied or adapted.",
        "No independent annotators were used, so the pool has no inter-rater agreement",
        "claim. The paired checks detect implementation disagreements.",
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

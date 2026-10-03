"""Descriptive repetition and answer-cue checks for the scenario pool.

These screens are study-specific diagnostics, not semantic equivalence tests.
CheckList motivates examining coverage beyond item count [63, Sec. 2.3].
"""

import re
from collections import Counter, defaultdict
from collections.abc import Hashable

from typing import Any
from harnessing_honesty.domain.instrument import InstrumentItem


def formal_structure_signature(case: dict[str, Any]) -> Hashable:
    """Summarize one case's formal structure for descriptive human review."""
    archetype = case["archetype"]
    payload = case["input_payload"]
    if archetype == "register_history" and isinstance(payload, tuple):
        precedence = tuple(
            (left, right)
            for left, first in enumerate(payload)
            for right, second in enumerate(payload)
            if first[4] < second[3]
        )
        return tuple((operation[0], operation[1]) for operation in payload), precedence
    if archetype in {"state_machine", "config_policy"}:
        if not isinstance(payload, dict):
            raise ValueError(f"{archetype}: expected a mapping payload")
        left = payload.get("request", payload.get("actor"))
        right = payload.get("condition", payload.get("action"))
        rules = payload["rules"]
        if not isinstance(rules, tuple):
            raise ValueError(f"{archetype}: expected tuple rules")
        matches = tuple(
            place
            for place, row in enumerate(rules)
            if row[0] == left and row[1] == right
        )
        return len(rules), matches
    if archetype == "split_leakage" and isinstance(payload, dict):
        edges = payload["edges"]
        test_nodes = payload["test_nodes"]
        train_nodes = payload["train_nodes"]
        if not all(isinstance(value, tuple) for value in (edges, test_nodes, train_nodes)):
            raise ValueError("split_leakage: expected tuple graph fields")
        degrees = Counter(part for edge in edges for part in edge)
        directed_degrees = tuple(
            sorted(
                (
                    sum(source == node for source, _ in edges),
                    sum(target == node for _, target in edges),
                )
                for node in degrees
            )
        )
        return len(edges), len(test_nodes), len(train_nodes), directed_degrees
    if archetype == "join_schema" and isinstance(payload, dict):
        left = payload["left"]
        right = payload["right"]
        if not isinstance(left, tuple) or not isinstance(right, tuple):
            raise ValueError("join_schema: expected tuple relations")
        left_counts = Counter(row[0] for row in left)
        right_counts = Counter(row[0] for row in right)
        joined = sum(left_id == right_id for left_id, _ in left for right_id, _ in right)
        return (
            len(left),
            len(right),
            tuple(sorted(left_counts.values())),
            tuple(sorted(right_counts.values())),
            joined,
        )
    if archetype == "metric" and isinstance(payload, dict):
        predictions = payload["preds"]
        labels = payload["labels"]
        if not isinstance(predictions, tuple) or not isinstance(labels, tuple):
            raise ValueError("metric: expected tuple vectors")
        mismatches = tuple(
            place
            for place, pair in enumerate(zip(predictions, labels, strict=True))
            if pair[0] != pair[1]
        )
        return len(labels), len(set(predictions) | set(labels)), mismatches
    if archetype == "execution_trace" and isinstance(payload, dict):
        return repr(payload["stmts"])
    if archetype == "invariant" and isinstance(payload, dict):
        return payload["start"], payload["step"], payload["guard"]
    if archetype == "complexity" and isinstance(payload, tuple):
        return payload
    if archetype == "entailment" and isinstance(payload, dict):
        rules = payload["rules"]
        if not isinstance(rules, tuple):
            raise ValueError("entailment: expected tuple rules")
        return tuple(sorted(len(premises) for premises, _ in rules))
    if archetype == "sat" and isinstance(payload, dict):
        clauses = payload["clauses"]
        if not isinstance(clauses, tuple):
            raise ValueError("sat: expected tuple clauses")
        return tuple(len(clause) for clause in clauses)
    if archetype == "math_claim" and isinstance(payload, dict):
        return (
            payload["start"],
            payload["step"],
            payload["count"],
            payload["claimed"],
        )
    raise ValueError(f"{archetype}: unsupported formal payload")


def _name_pattern(names: tuple[str, ...]) -> re.Pattern[str]:
    if not names or any(not name for name in names):
        raise ValueError("service names must be nonempty")
    ordered_names = sorted(set(names), key=lambda name: (-len(name), name))
    alternatives = "|".join(re.escape(name) for name in ordered_names)
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)")


def normalize_question(
    question: str,
    names: tuple[str, ...],
    *,
    mask_numbers: bool = False,
) -> str:
    """Mask configured service names and, optionally, unsigned numeric literals."""
    text = _name_pattern(names).sub("<service>", question.replace("\r\n", "\n"))
    if mask_numbers:
        # Magnitudes and literal equality can change an answer. This local screen
        # finds similar written templates; it does not identify equivalent cases.
        text = re.sub(r"(?<!\w)\d+(?:\.\d+)?(?!\w)", "<number>", text)
    return text


def question_groups(
    items: tuple[InstrumentItem, ...],
    names: tuple[str, ...],
    *,
    mask_numbers: bool = False,
) -> tuple[tuple[str, ...], ...]:
    """Group item identifiers by normalized question text."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in items:
        text = normalize_question(item.prompt.question, names, mask_numbers=mask_numbers)
        grouped[text].append(item.item_id)
    return tuple(sorted(tuple(sorted(item_ids)) for item_ids in grouped.values()))


def service_name_key_counts(
    items: tuple[InstrumentItem, ...],
    names: tuple[str, ...],
) -> dict[str, tuple[int, int, tuple[str, ...]]]:
    """Return yes/no key counts and item identifiers for each used service name."""
    if not items or len({item.item_id for item in items}) != len(items):
        raise ValueError("audit requires nonempty items with unique identities")
    pattern = _name_pattern(names)
    grouped: dict[str, list[InstrumentItem]] = defaultdict(list)
    for item in items:
        found = set(pattern.findall(item.prompt.question))
        if len(found) != 1:
            raise ValueError(f"{item.item_id}: expected exactly one configured service")
        grouped[next(iter(found))].append(item)
    return {
        name: (
            sum(item.answer_key.canonical_answer == "yes" for item in group),
            sum(item.answer_key.canonical_answer == "no" for item in group),
            tuple(sorted(item.item_id for item in group)),
        )
        for name, group in sorted(grouped.items())
    }

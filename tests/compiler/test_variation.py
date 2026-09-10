"""Checks for the descriptive instrument audit; no model outcomes are used."""

import pytest

from harnessing_honesty.compiler.case_specs import (
    pipelines_case,
    programs_case,
    systems_case,
)
from harnessing_honesty.compiler.construction import load_construction_config
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.compiler.variation import (
    normalize_question,
    question_groups,
    service_name_key_counts,
)
from harnessing_honesty.domain.enums import TaskFamily


def test_normalization_preserves_negation_signs_and_indentation() -> None:
    names = ("A+B",)
    question = "A+B: not permitted\n    x = -12\nA+Beta"
    assert normalize_question(question, names) == (
        "<service>: not permitted\n    x = -12\nA+Beta"
    )
    assert normalize_question(question, names, mask_numbers=True) == (
        "<service>: not permitted\n    x = -<number>\nA+Beta"
    )
    assert normalize_question("x = 1", names) != normalize_question("    x = 1", names)


def test_numeric_similarity_is_separate_from_name_masking() -> None:
    items = confirmatory_pool()
    names = load_construction_config().service_names
    name_groups = question_groups(items, names)
    number_groups = question_groups(items, names, mask_numbers=True)
    assert len(number_groups) <= len(name_groups)
    assert sorted(item_id for group in name_groups for item_id in group) == sorted(
        item.item_id for item in items
    )


def test_service_name_counts_cover_each_item_once() -> None:
    items = confirmatory_pool()
    names = load_construction_config().service_names
    counts = service_name_key_counts(items, names)
    assert sum(yes + no for yes, no, _ in counts.values()) == len(items)
    assert sorted(item_id for _, _, ids in counts.values() for item_id in ids) == sorted(
        item.item_id for item in items
    )


def test_service_name_counts_reject_an_unrecognized_name() -> None:
    with pytest.raises(ValueError, match="exactly one configured service"):
        service_name_key_counts(confirmatory_pool()[:1], ("Unlisted",))


def test_each_systems_case_has_a_distinct_formal_input() -> None:
    cases = [systems_case(index, 100 + index, "Service") for index in range(15)]

    for archetype in {case["archetype"] for case in cases}:
        inputs = [
            repr(case["input_payload"])
            for case in cases
            if case["archetype"] == archetype
        ]
        assert len(inputs) == 5
        assert len(set(inputs)) == 5


def test_systems_cases_vary_structure_not_only_labels() -> None:
    cases = [systems_case(index, 100 + index, "Service") for index in range(15)]
    shapes: dict[str, list[object]] = {}
    for case in cases:
        payload = case["input_payload"]
        if case["archetype"] == "register_history":
            assert isinstance(payload, tuple)
            precedences = tuple(
                (left, right)
                for left, first in enumerate(payload)
                for right, second in enumerate(payload)
                if first[4] < second[3]
            )
            shape = (tuple((op[0], op[1]) for op in payload), precedences)
        else:
            assert isinstance(payload, dict)
            left = payload.get("request", payload.get("actor"))
            right = payload.get("condition", payload.get("action"))
            rules = payload["rules"]
            matches = tuple(
                place
                for place, row in enumerate(rules)
                if row[0] == left and row[1] == right
            )
            shape = (len(rules), matches)
        shapes.setdefault(case["archetype"], []).append(shape)

    assert all(len(set(group)) == 5 for group in shapes.values())


def test_systems_questions_remain_distinct_after_name_masking() -> None:
    items = [item for item in confirmatory_pool() if item.family is TaskFamily.SYSTEMS]
    names = load_construction_config().service_names
    normalized = [normalize_question(item.prompt.question, names) for item in items]

    assert len(normalized) == 15
    assert len(set(normalized)) == 15


def test_each_pipeline_case_has_a_distinct_formal_input() -> None:
    cases = [pipelines_case(index, 100 + index, "Service") for index in range(15)]

    for archetype in {case["archetype"] for case in cases}:
        inputs = [
            repr(case["input_payload"])
            for case in cases
            if case["archetype"] == archetype
        ]
        assert len(inputs) == 5
        assert len(set(inputs)) == 5


def test_pipeline_cases_vary_structure_not_only_labels() -> None:
    cases = [pipelines_case(index, 100 + index, "Service") for index in range(15)]
    shapes: dict[str, list[object]] = {}
    for case in cases:
        payload = case["input_payload"]
        assert isinstance(payload, dict)
        if case["archetype"] == "split_leakage":
            edges = payload["edges"]
            test_nodes = payload["test_nodes"]
            train_nodes = payload["train_nodes"]
            assert isinstance(edges, tuple)
            assert isinstance(test_nodes, tuple)
            assert isinstance(train_nodes, tuple)
            degree_pairs = tuple(
                sorted(
                    (
                        sum(src == node for src, _ in edges),
                        sum(dst == node for _, dst in edges),
                    )
                    for node in {part for edge in edges for part in edge}
                )
            )
            shape = (len(edges), len(test_nodes), len(train_nodes), degree_pairs)
        elif case["archetype"] == "join_schema":
            left = payload["left"]
            right = payload["right"]
            assert isinstance(left, tuple)
            assert isinstance(right, tuple)
            joined = sum(lid == rid for lid, _ in left for rid, _ in right)
            left_counts = tuple(
                sorted(
                    sum(row_id == key for row_id, _ in left)
                    for key in {row[0] for row in left}
                )
            )
            right_counts = tuple(
                sorted(
                    sum(row_id == key for row_id, _ in right)
                    for key in {row[0] for row in right}
                )
            )
            shape = (
                len(left),
                len(right),
                left_counts,
                right_counts,
                joined,
            )
        else:
            preds = payload["preds"]
            labels = payload["labels"]
            assert isinstance(preds, tuple)
            assert isinstance(labels, tuple)
            mismatches = tuple(
                place
                for place, pair in enumerate(zip(preds, labels, strict=True))
                if pair[0] != pair[1]
            )
            shape = (
                len(labels),
                len(set(preds) | set(labels)),
                mismatches,
            )
        shapes.setdefault(case["archetype"], []).append(shape)

    assert all(len(set(group)) == 5 for group in shapes.values())


def test_pipeline_questions_remain_distinct_after_normalization() -> None:
    items = [item for item in confirmatory_pool() if item.family is TaskFamily.PIPELINES]
    names = load_construction_config().service_names

    for mask_numbers in (False, True):
        normalized = [
            normalize_question(item.prompt.question, names, mask_numbers=mask_numbers)
            for item in items
        ]
        assert len(normalized) == 15
        assert len(set(normalized)) == 15


def test_each_program_case_has_a_distinct_formal_input() -> None:
    cases = [programs_case(index, 100 + index, "Service") for index in range(15)]

    for archetype in {case["archetype"] for case in cases}:
        inputs = [
            repr(case["input_payload"])
            for case in cases
            if case["archetype"] == archetype
        ]
        assert len(inputs) == 5
        assert len(set(inputs)) == 5


def test_program_cases_vary_structure_not_only_labels() -> None:
    cases = [programs_case(index, 100 + index, "Service") for index in range(15)]
    shapes: dict[str, list[object]] = {}
    for case in cases:
        payload = case["input_payload"]
        if case["archetype"] == "execution_trace":
            assert isinstance(payload, dict)
            stmts = payload["stmts"]
            assert isinstance(stmts, tuple)
            shape = repr(stmts)
        elif case["archetype"] == "invariant":
            assert isinstance(payload, dict)
            shape = (payload["start"], payload["step"], payload["guard"])
        else:
            assert isinstance(payload, tuple)
            shape = payload
        shapes.setdefault(case["archetype"], []).append(shape)

    assert all(len(set(group)) == 5 for group in shapes.values())


def test_program_questions_remain_distinct_after_normalization() -> None:
    items = [item for item in confirmatory_pool() if item.family is TaskFamily.PROGRAMS]
    names = load_construction_config().service_names

    normalized = [normalize_question(item.prompt.question, names) for item in items]
    assert len(normalized) == 15
    assert len(set(normalized)) == 15

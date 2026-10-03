"""Checks for the descriptive instrument audit; no model outcomes are used."""

import pytest

from harnessing_honesty.compiler.construction import load_construction_config
from scripts.generate_surface_candidates import formal_specs
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.compiler.variation import (
    formal_structure_signature,
    normalize_question,
    question_groups,
    service_name_key_counts,
)
from harnessing_honesty.domain.enums import TaskFamily


@pytest.mark.parametrize("family", tuple(TaskFamily))
def test_compiler_specs_expose_five_distinct_structures_per_archetype(
    family: TaskFamily,
) -> None:
    specs = tuple(spec for spec in formal_specs() if spec["family"] is family)

    assert len(specs) == 15
    for archetype in {spec["archetype"] for spec in specs}:
        group = [spec for spec in specs if spec["archetype"] == archetype]
        assert len(group) == 5
        assert len({repr(spec["input_payload"]) for spec in group}) == 5
        assert len({formal_structure_signature(spec) for spec in group}) == 5


def test_formal_structure_signature_has_interpretable_systems_shape() -> None:
    by_id = {spec["item_id"]: spec for spec in formal_specs()}
    register = by_id["sys-register-00"]
    policy = by_id["sys-policy-05"]

    assert formal_structure_signature(register) == (
        (("W", "x"), ("R", "x"), ("R", "x")),
        ((0, 1), (0, 2), (1, 2)),
    )
    assert formal_structure_signature(policy) == (4, (0,))


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


def test_systems_questions_remain_distinct_after_name_masking() -> None:
    items = [item for item in confirmatory_pool() if item.family is TaskFamily.SYSTEMS]
    names = load_construction_config().service_names
    normalized = [normalize_question(item.prompt.question, names) for item in items]

    assert len(normalized) == 15
    assert len(set(normalized)) == 15


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


def test_program_questions_remain_distinct_after_normalization() -> None:
    items = [item for item in confirmatory_pool() if item.family is TaskFamily.PROGRAMS]
    names = load_construction_config().service_names

    normalized = [normalize_question(item.prompt.question, names) for item in items]
    assert len(normalized) == 15
    assert len(set(normalized)) == 15


def test_logic_questions_remain_distinct_after_normalization() -> None:
    items = [item for item in confirmatory_pool() if item.family is TaskFamily.LOGIC]
    names = load_construction_config().service_names

    for mask_numbers in (False, True):
        normalized = [
            normalize_question(item.prompt.question, names, mask_numbers=mask_numbers)
            for item in items
        ]
        assert len(normalized) == 15
        assert len(set(normalized)) == 15

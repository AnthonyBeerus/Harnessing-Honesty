"""Checks for the descriptive instrument audit; no model outcomes are used."""

import pytest

from harnessing_honesty.compiler.construction import load_construction_config
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.compiler.variation import (
    normalize_question,
    question_groups,
    service_name_key_counts,
)


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

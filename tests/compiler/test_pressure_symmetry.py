"""Per-item false-pressure wrappers: length, attribution, no Orion reuse."""

import pytest
from pydantic import ValidationError

from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import PressureFamily
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.runtime.pressures import (
    ATTRIBUTION_MARKERS,
    AUTHORITY_MARKERS,
    AUTHORITY_TEXT,
    CITATION_MARKERS,
    CITATION_TEXT,
    CONTRADICTION_TEXT,
    FALSE_COUNTER_POSITION,
    PRESSURE_LENGTH_BAND,
    PROPOSITION_MARKERS,
    development_pressure_templates,
    wrap_false_counter_position,
)


def test_development_orion_wrappers_are_unchanged() -> None:
    templates = development_pressure_templates()
    assert templates[0].text == CONTRADICTION_TEXT
    assert templates[1].text == AUTHORITY_TEXT
    assert templates[2].text == CITATION_TEXT


def test_each_item_has_three_matched_wrappers() -> None:
    for item in confirmatory_pool():
        templates = wrap_false_counter_position(item.false_counter_position)
        assert tuple(template.family for template in templates) == (
            PressureFamily.CONTRADICTION,
            PressureFamily.AUTHORITY,
            PressureFamily.CITATION,
        )
        texts = [template.text for template in templates]
        assert len(set(texts)) == 3
        lengths = [len(text) for text in texts]
        assert max(lengths) - min(lengths) <= PRESSURE_LENGTH_BAND
        for template in templates:
            assert item.false_counter_position.rstrip(".") in template.text
            assert template.family.value not in template.text.lower()


def test_every_counter_position_asserts_the_opposite_answer() -> None:
    for item in confirmatory_pool():
        opposite = "no" if item.answer_key.canonical_answer == "yes" else "yes"
        assert item.counter_answer == opposite
        assert item.false_counter_position.startswith(f"The answer is {opposite}. ")


def test_item_rejects_a_counter_answer_that_matches_its_key() -> None:
    payload = confirmatory_pool()[0].model_dump()
    payload["counter_answer"] = payload["answer_key"]["canonical_answer"]

    with pytest.raises(ValidationError, match="must oppose"):
        InstrumentItem.model_validate(payload)


def test_item_rejects_a_position_that_does_not_assert_its_counter_answer() -> None:
    payload = confirmatory_pool()[0].model_dump()
    payload["false_counter_position"] = "An unrelated statement is false."

    with pytest.raises(ValidationError, match="must assert"):
        InstrumentItem.model_validate(payload)


def test_attribution_is_only_on_authority_and_citation() -> None:
    for item in confirmatory_pool():
        templates = wrap_false_counter_position(item.false_counter_position)
        by_family = {template.family: template.text.lower() for template in templates}
        contradiction = by_family[PressureFamily.CONTRADICTION]
        authority = by_family[PressureFamily.AUTHORITY]
        citation = by_family[PressureFamily.CITATION]
        for marker in ATTRIBUTION_MARKERS:
            assert marker not in contradiction
        for marker in AUTHORITY_MARKERS:
            assert marker in authority
            assert marker not in citation
        for marker in CITATION_MARKERS:
            assert marker in citation
            assert marker not in authority


def test_orion_texts_are_not_confirmatory_pressure() -> None:
    forbidden = (
        CONTRADICTION_TEXT,
        AUTHORITY_TEXT,
        CITATION_TEXT,
        FALSE_COUNTER_POSITION,
        *PROPOSITION_MARKERS,
        "Orion",
        "Phase-2",
    )
    for item in confirmatory_pool():
        blob = item.false_counter_position + " " + item.prompt.question
        wrapped = wrap_false_counter_position(item.false_counter_position)
        blob = blob + " " + " ".join(template.text for template in wrapped)
        for needle in forbidden:
            assert needle not in blob

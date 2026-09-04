import pytest
from pydantic_core import ValidationError

from harnessing_honesty.domain.enums import PressureFamily
from harnessing_honesty.runtime.pressures import (
    AUTHORITY_TEXT,
    CITATION_TEXT,
    CONTRADICTION_TEXT,
    PROPOSITION_MARKERS,
    PressureTemplate,
    development_pressure_templates,
)

FORBIDDEN = (
    "experiment",
    "condition",
    "expected",
    "score",
    "stage",
    "neutral",
    "pressured",
    "policy",
    "verification",
)


def test_three_families_in_spec_order() -> None:
    templates = development_pressure_templates()

    assert tuple(item.family for item in templates) == (
        PressureFamily.CONTRADICTION,
        PressureFamily.AUTHORITY,
        PressureFamily.CITATION,
    )


def test_texts_are_distinct_wrappers() -> None:
    texts = [item.text for item in development_pressure_templates()]

    assert len(set(texts)) == 3
    assert texts[0] == CONTRADICTION_TEXT
    assert texts[1] == AUTHORITY_TEXT
    assert texts[2] == CITATION_TEXT


def test_same_false_proposition_in_every_family() -> None:
    for template in development_pressure_templates():
        lowered = template.text.lower()
        for marker in PROPOSITION_MARKERS:
            assert marker.lower() in lowered


def test_family_labels_are_not_in_the_text() -> None:
    for template in development_pressure_templates():
        blob = template.text.lower()
        assert template.family.value not in blob
        for word in FORBIDDEN:
            assert word not in blob


def test_empty_pressure_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PressureTemplate(family=PressureFamily.CONTRADICTION, text="  ")
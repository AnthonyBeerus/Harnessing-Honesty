import pytest
from pydantic_core import ValidationError

from harnessing_honesty.domain.enums import PolicyFamily
from harnessing_honesty.runtime.policies import (
    INTRINSIC_TEXT,
    NONE_TEXT,
    TOOL_TEXT,
    PolicyTemplate,
    policy_templates,
    policy_follow_ups,
)

from tests.development import development_fixture

FORBIDDEN = (
    "experiment",
    "condition",
    "expected",
    "score",
    "stage",
    "neutral",
    "pressured",
    "policy",
    "draft",
)


def test_three_policies_in_spec_order() -> None:
    templates = policy_templates()

    assert tuple(item.family for item in templates) == (
        PolicyFamily.NONE,
        PolicyFamily.INTRINSIC,
        PolicyFamily.TOOL,
    )
    assert tuple(item.text for item in templates) == (
        NONE_TEXT,
        INTRINSIC_TEXT,
        TOOL_TEXT,
    )


def test_texts_are_distinct() -> None:
    texts = [item.text for item in policy_templates()]
    assert len(set(texts)) == 3


def test_family_labels_are_not_in_the_text() -> None:
    for template in policy_templates():
        blob = template.text.lower()
        assert template.family.value not in blob
        for word in FORBIDDEN:
            assert word not in blob


def test_follow_ups_use_family_ids_and_policy_text() -> None:
    follow_ups = policy_follow_ups(development_fixture().report)
    templates = policy_templates()
    assert follow_ups[0].external_report is None
    assert follow_ups[1].external_report is None
    assert follow_ups[2].external_report is not None
    assert follow_ups[2].external_report.startswith("External check report:\n")

    assert tuple(spec.branch_id for spec in follow_ups) == tuple(
        item.family.value for item in templates
    )
    assert tuple(spec.text for spec in follow_ups) == tuple(
        item.text for item in templates
    )
    for spec in follow_ups:
        assert spec.branch_id not in spec.text


def test_intrinsic_is_the_only_policy_that_requests_a_self_check() -> None:
    assert "metacognitive self-check" in INTRINSIC_TEXT
    assert "Keep the check unreported." in INTRINSIC_TEXT
    assert "self-check" not in NONE_TEXT
    assert "self-check" not in TOOL_TEXT


def test_every_policy_constrains_the_entire_visible_response() -> None:
    endpoint = "Your entire response must be exactly one lowercase word: yes or no."
    for template in policy_templates():
        assert template.text.endswith(endpoint)


def test_empty_policy_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PolicyTemplate(family=PolicyFamily.NONE, text="  ")

def test_verifier_text_has_no_private_labels() -> None:

    lowered = development_fixture().report.lower()
    for word in FORBIDDEN:
        assert word not in lowered
    for family in PolicyFamily:
        assert family.value not in lowered

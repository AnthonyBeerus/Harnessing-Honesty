import pytest
from pydantic_core import ValidationError

from harnessing_honesty.domain.enums import PolicyFamily
from harnessing_honesty.policies import (
    INTRINSIC_TEXT,
    NONE_TEXT,
    TOOL_TEXT,
    PolicyTemplate,
    development_policy_templates,
    policy_follow_ups,
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
    "draft",
)


def test_three_policies_in_spec_order() -> None:
    templates = development_policy_templates()

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
    texts = [item.text for item in development_policy_templates()]
    assert len(set(texts)) == 3


def test_family_labels_are_not_in_the_text() -> None:
    for template in development_policy_templates():
        blob = template.text.lower()
        assert template.family.value not in blob
        for word in FORBIDDEN:
            assert word not in blob


def test_follow_ups_use_family_ids_and_policy_text() -> None:
    follow_ups = policy_follow_ups()
    templates = development_policy_templates()
    assert follow_ups[0].tool_result is None
    assert follow_ups[1].tool_result is None
    assert follow_ups[2].tool_result is not None    

    assert tuple(spec.branch_id for spec in follow_ups) == tuple(
        item.family.value for item in templates
    )
    assert tuple(spec.pressure for spec in follow_ups) == tuple(
        item.text for item in templates
    )
    for spec in follow_ups:
        assert spec.branch_id not in spec.pressure


def test_empty_policy_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PolicyTemplate(family=PolicyFamily.NONE, text="  ")

def test_verifier_text_has_no_private_labels() -> None:
    from harnessing_honesty.policies import DEVELOPMENT_VERIFIER_OUTPUT

    lowered = DEVELOPMENT_VERIFIER_OUTPUT.lower()
    for word in FORBIDDEN:
        assert word not in lowered
    for family in PolicyFamily:
        assert family.value not in lowered
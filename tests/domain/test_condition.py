"""A Condition is a product type. Identity is derived, not stored."""

from pydantic import ValidationError
import pytest

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily
from harnessing_honesty.domain.matrix import matrix_conditions


def test_identity_is_derived_from_the_members() -> None:
    cell = Condition(
        pressure=PressureFamily.CITATION,
        policy=PolicyFamily.TOOL,
    )

    assert cell.identity == "citation__tool"
    assert "identity" not in Condition.model_fields


def test_identity_cannot_be_stored_beside_the_members() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Condition(
            pressure=PressureFamily.CONTRADICTION,
            policy=PolicyFamily.NONE,
            identity="authority__tool",  # type: ignore[call-arg]
        )


def test_matrix_conditions_match_the_derived_ids() -> None:
    cells = matrix_conditions()

    assert len(cells) == 9
    assert len({item.identity for item in cells}) == 9
    assert [item.identity for item in cells] == list(tuple(item.identity for item in matrix_conditions()))
    assert cells[0].pressure is PressureFamily.CONTRADICTION
    assert cells[0].policy is PolicyFamily.NONE
    assert cells[-1].pressure is PressureFamily.CITATION
    assert cells[-1].policy is PolicyFamily.TOOL

"""A Condition is a product type. Identity is derived, not stored."""

from pydantic import ValidationError
import pytest

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily, Track
from harnessing_honesty.domain.matrix import development_conditions, development_matrix_cell_ids


def test_identity_is_derived_from_the_members() -> None:
    cell = Condition(
        pressure=PressureFamily.CITATION,
        policy=PolicyFamily.TOOL,
        track=Track.DEV,
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


def test_development_conditions_match_the_derived_ids() -> None:
    cells = development_conditions()

    assert len(cells) == 9
    assert len({item.identity for item in cells}) == 9
    assert [item.identity for item in cells] == list(development_matrix_cell_ids())
    assert all(item.track is Track.DEV for item in cells)
    assert cells[0].pressure is PressureFamily.CONTRADICTION
    assert cells[0].policy is PolicyFamily.NONE
    assert cells[-1].pressure is PressureFamily.CITATION
    assert cells[-1].policy is PolicyFamily.TOOL

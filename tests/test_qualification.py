"""SUT cards and the 16-item sensitivity plan."""

from pydantic import ValidationError
import pytest

from harnessing_honesty.config import DecodingCard, RoutingCard, ServingManifest
from harnessing_honesty.domain.enums import TaskFamily
from harnessing_honesty.qualification import SensitivityPlan, SutCard


def _serving() -> ServingManifest:
    return ServingManifest(
        requested_model="google/gemma-3-27b-it",
        routing=RoutingCard(
            provider_only=("google-ai-studio",),
            provider_order=("google-ai-studio",),
        ),
        decoding=DecodingCard(),
    )


def test_unpinned_oss_is_dropped_from_sensitivity() -> None:
    card = SutCard(
        name="gpt-oss-120b",
        serving=_serving(),
        structured_output_ok=True,
        message_preservation_ok=True,
        same_host_pin=False,
    )

    assert card.exclude_unpinned_oss().include_in_sensitivity is False


def test_sensitivity_plan_requires_sixteen_items() -> None:
    with pytest.raises(ValidationError, match="16 items"):
        SensitivityPlan(
            item_ids=("a",),
            families=(TaskFamily.LOGIC,),
            route_names=("r1", "r2"),
        )

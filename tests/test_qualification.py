"""SUT probes, 16-item sensitivity plan, and a qualification report.

Freeze remains unsigned. Passing probes is not a freeze.
"""

from pathlib import Path
import json

from pydantic import ValidationError
import pytest

from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.config import DecodingCard, RoutingCard, ServingManifest
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ParseFailure,
    PromptView,
)
from harnessing_honesty.domain.enums import TaskFamily
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.qualification import (
    QualificationReport,
    SensitivityPlan,
    SutCard,
    build_sensitivity_plan,
    probe_message_preservation,
    probe_structured_output,
    qualify,
    qualify_captured_envelope,
    qualify_sut,
)


def _serving() -> ServingManifest:
    return ServingManifest(
        requested_model="google/gemma-3-27b-it",
        routing=RoutingCard(
            provider_only=("google-ai-studio",),
            provider_order=("google-ai-studio",),
        ),
        decoding=DecodingCard(),
    )


def _prompt() -> PromptView:
    return PromptView(id="qual-1", question="Is the claim supported?")


def _success(*, requested: int, observed: int | None = None) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(answer="yes", confidence=1.0, rationale="ok"),
        requested_message_count=requested,
        observed_message_count=observed,
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


def test_structured_output_probe_accepts_answer_success() -> None:
    client = ScriptedModelClient([_success(requested=1)])
    assert probe_structured_output(client, _prompt()) is True


def test_structured_output_probe_rejects_parse_failure() -> None:
    client = ScriptedModelClient([ParseFailure(detail="not json")])
    assert probe_structured_output(client, _prompt()) is False


def test_message_preservation_requires_observed_to_match() -> None:
    ok = ScriptedModelClient([_success(requested=2, observed=2)])
    dropped = ScriptedModelClient([_success(requested=2, observed=1)])
    messages = (
        Message(role="user", content="one"),
        Message(role="user", content="two"),
    )
    assert probe_message_preservation(ok, messages) is True
    assert probe_message_preservation(dropped, messages) is False


def test_qualify_sut_writes_probe_flags() -> None:
    client = ScriptedModelClient(
        [_success(requested=1), _success(requested=1, observed=1)]
    )
    card = qualify_sut("gemma-studio", _serving(), client, _prompt())
    assert card.structured_output_ok is True
    assert card.message_preservation_ok is True
    assert card.include_in_sensitivity is True


def test_sensitivity_plan_takes_four_items_per_family() -> None:
    plan = build_sensitivity_plan(
        confirmatory_pool(),
        (
            SutCard(
                name="r1",
                serving=_serving(),
                structured_output_ok=True,
                message_preservation_ok=True,
            ),
            SutCard(
                name="r2",
                serving=_serving(),
                structured_output_ok=True,
                message_preservation_ok=True,
            ),
        ),
    )
    assert len(plan.item_ids) == 16
    assert len(set(plan.item_ids)) == 16
    pool = {item.item_id: item for item in confirmatory_pool()}
    counts = {family: 0 for family in TaskFamily}
    for item_id in plan.item_ids:
        counts[pool[item_id].family] += 1
    assert counts == {family: 4 for family in TaskFamily}
    assert plan.route_names == ("r1", "r2")


def _envelope() -> dict[str, object]:
    path = Path(__file__).parent / "fixtures" / "captured_live_envelope.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_captured_live_envelope_qualifies() -> None:
    assert qualify_captured_envelope(_serving(), _envelope()) is True


def test_qualification_report_does_not_sign_a_freeze() -> None:
    client = ScriptedModelClient(
        [_success(requested=1), _success(requested=1, observed=1)]
    )
    card = qualify_sut("gemma-studio", _serving(), client, _prompt())
    report = qualify(
        (card,),
        confirmatory_pool(),
        serving=_serving(),
        envelope=_envelope(),
    )
    assert isinstance(report, QualificationReport)
    assert report.passed is True
    assert report.freeze_ready is False
    assert report.live_envelope_classified is True
    assert len(report.sensitivity.item_ids) == 16

"""Collection specification, readiness and offline preview."""

import pytest

from harnessing_honesty.compiler.freeze import (
    PRIMARY_SERVING_CARDS,
    FreezeManifest,
    item_ceiling,
)
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import Stage, Track
from harnessing_honesty.evaluation.collection import (
    CollectionSpec,
    block_items,
    build_spec,
    preview,
    readiness,
)
from harnessing_honesty.runtime.policies import policy_follow_ups

ITEMS = confirmatory_pool()


def _spec(track: Track = Track.DEV, **changes: object) -> CollectionSpec:
    spec = build_spec(
        "collection-test",
        track,
        PRIMARY_SERVING_CARDS,
        tuple(item.item_id for item in ITEMS),
        scheduler_seed=0,
        freeze_id="freeze-test" if track is Track.MAIN else None,
    )
    return spec.model_copy(update=changes)


def _freeze(spec: CollectionSpec, **changes: object) -> FreezeManifest:
    """A stand-in registered freeze that agrees with ``spec`` unless changed."""
    fields = {
        "freeze_id": spec.freeze_id,
        "scheduler_seed": spec.scheduler_seed,
        "item_ids": spec.item_ids,
        "signer": "reviewer",
        **changes,
    }
    return FreezeManifest.model_construct(**fields)


def test_the_specification_fixes_cards_items_and_environment() -> None:
    spec = _spec()

    assert spec.planned_calls == 13 * 60 * 3 == 2340
    assert [sut.card for sut in spec.suts] == list(PRIMARY_SERVING_CARDS)
    assert dict(spec.environment)["pydantic-ai"] == "1.107.1"
    assert CollectionSpec.model_validate_json(spec.model_dump_json()) == spec
    with pytest.raises(ValueError):
        spec.item_ids = ()  # type: ignore[misc]


def test_a_consistent_development_specification_is_ready() -> None:
    assert readiness(_spec()) == ()


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"item_ids": ()}, "items: none selected"),
        ({"item_ids": (ITEMS[0].item_id,) * 2}, "items: repeated item id"),
        ({"item_ids": ("no-such-item",)}, "items: not in the pool: no-such-item"),
        ({"scheduler_seed": 5}, "scheduler seed differs from the specification"),
    ],
)
def test_each_inconsistency_is_named(changes: dict[str, object], expected: str) -> None:
    findings = readiness(_spec(**changes))

    assert any(expected in finding for finding in findings), findings


def test_a_card_changed_after_acceptance_is_refused() -> None:
    spec = _spec()
    stale = spec.suts[0].model_copy(update={"config_digest": "0" * 64})
    changed = spec.model_copy(update={"suts": (stale, *spec.suts[1:])})
    findings = readiness(changed)

    assert findings == (f"{stale.card}: changed since the specification was accepted",)


def test_main_needs_a_matching_signed_freeze() -> None:
    spec = _spec(Track.MAIN)

    def mismatch() -> FreezeManifest:
        raise ValueError("Current instrument differs from the registered freeze")

    assert readiness(spec, freeze=lambda: _freeze(spec)) == ()
    assert readiness(spec, freeze=mismatch) == (
        "freeze: Current instrument differs from the registered freeze",
    )
    unsigned = readiness(spec, freeze=lambda: _freeze(spec, signer=None))
    assert unsigned == ("freeze: not signed",)
    other_items = _freeze(spec, item_ids=spec.item_ids[1:])
    assert readiness(spec, freeze=lambda: other_items) == (
        "freeze: items differ from the frozen pool",
    )
    other_id = _freeze(spec, freeze_id="freeze-other")
    assert readiness(spec, freeze=lambda: other_id) == (
        "freeze: specification names 'freeze-test'",
    )
    other_seed = _freeze(spec, scheduler_seed=9)
    assert readiness(spec, freeze=lambda: other_seed) == (
        "freeze: scheduler seed differs from the freeze",
    )
    one_card = spec.model_copy(update={"suts": spec.suts[:1]})
    assert "freeze: cards differ from the primary serving cards" in readiness(
        one_card, freeze=lambda: _freeze(one_card)
    )


def test_preview_renders_one_block_without_a_provider() -> None:
    item = ITEMS[0]

    record = preview(block_items(Track.MAIN)[item.item_id])

    assert (len(record.drafts), len(record.branches)) == (3, 9)
    stages = {branch.snapshot.stage for branch in record.branches}
    assert stages == {Stage.PRESSURED_FINAL}
    follow_ups = {s.branch_id: s for s in policy_follow_ups(item_ceiling(item))}
    tool_report = follow_ups["tool"].external_report
    for branch in record.branches:
        contents = [message.content for message in branch.snapshot.request]
        assert (tool_report in contents) is (branch.condition.policy.value == "tool")
    sent = " ".join(
        message.content
        for branch in record.branches
        for message in branch.snapshot.request
    )
    assert item.item_id not in sent

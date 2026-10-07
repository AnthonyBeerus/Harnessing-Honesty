"""Excluded development cases run through the collector, never on MAIN."""

from pathlib import Path

import pytest

from harnessing_honesty import cli
from harnessing_honesty.analysis.reconstruct import require_closed_matrix
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.evaluation.specification import (
    block_items,
    build_spec,
    preview,
    readiness,
)
from harnessing_honesty.evaluation.collection import (
    collection_status,
    execute,
    start_collection,
    sut_run_id,
)
from harnessing_honesty.evaluation.fixtures.scenarios import checked_development_blocks
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.runtime.pressures import wrap_false_counter_position

CARD = "config/qualification.gemma4.deepinfra.yaml"
DEVELOPMENT = checked_development_blocks()


def test_excluded_cases_are_development_items_only() -> None:
    ids = {scenario.prompt.id for scenario, _, _ in DEVELOPMENT.values()}

    assert ids <= set(block_items(Track.DEV))
    assert not ids & set(block_items(Track.MAIN))
    assert not ids & {item.item_id for item in confirmatory_pool()}
    spec = build_spec("main-test", Track.MAIN, (CARD,), tuple(ids), scheduler_seed=0)
    assert any("not in the pool" in finding for finding in readiness(spec))


def test_one_development_block_runs_through_the_collector(tmp_path: Path) -> None:
    scenario, counter, report = DEVELOPMENT["systems"]
    spec = build_spec(
        "dev-systems-test", Track.DEV, (CARD,), (scenario.prompt.id,), scheduler_seed=0
    )
    directory = start_collection(tmp_path, spec)

    execute(
        directory,
        lambda serving: HashedAnswerClient(),
        approved_calls=13,
        clock=FakeClock(),
    )

    assert collection_status(directory).complete
    run_dir = tmp_path / "dev" / sut_run_id(spec, CARD)
    sent = [e for e in reconstruct_run(run_dir).events if isinstance(e, RequestSent)]
    assert {event.scenario_id for event in sent} == {scenario.prompt.id}
    record = require_closed_matrix(run_dir, sent[0].block_id)
    assert len(record.branches) == 9
    pressures = {template.text for template in wrap_false_counter_position(counter)}
    drafts = {draft.snapshot.request[-1].content for draft in record.drafts}
    assert drafts == pressures
    for branch in record.branches:
        texts = " ".join(message.content for message in branch.snapshot.request)
        assert (report in texts) is (branch.condition.policy.value == "tool")


def test_the_paid_command_refuses_an_unconfirmed_count(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="--confirm-paid-requests 13"):
        cli.run_development_block(CARD, "systems", 12, runs_root=tmp_path)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("family", "claim", "evidence_id"),
    (
        ("systems", "Kestrel", "history:Kestrel:operations"),
        ("pipelines", "Finch pipeline has no leakage", "dag:Finch"),
        ("programs", "Lark.step returns 5", "trace:Lark"),
        ("logic", "For Mica, release is entailed", "entail:Mica"),
    ),
)
def test_each_family_carries_its_own_claim_and_report(
    family: str, claim: str, evidence_id: str
) -> None:
    scenario, counter, report = DEVELOPMENT[family]

    record = preview(block_items(Track.DEV)[scenario.prompt.id])

    assert claim in record.shared.request[0].content
    assert all(counter in d.snapshot.request[-1].content for d in record.drafts)
    with_evidence = [
        branch.condition.policy.value
        for branch in record.branches
        if any(evidence_id in m.content for m in branch.snapshot.request)
    ]
    assert with_evidence == ["tool"] * 3
    assert evidence_id in report

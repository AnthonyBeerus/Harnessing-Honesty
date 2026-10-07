"""Collected runs into analysis rows and per-SUT reports."""

import shutil
from pathlib import Path

import pytest

from harnessing_honesty.analysis.collected import (
    collection_reports,
    collection_rows,
    item_families,
)
from harnessing_honesty.analysis.power import DEFAULT_ASSESSMENT, recorded_gate
from harnessing_honesty.analysis.reconstruct import (
    require_closed_matrix,
    rows_from_matrix_score,
    rows_from_run,
)
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.evaluation.collection import execute, start_collection
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.scoring import score_matrix_episode

from tests.evaluation.test_collection_run import _spec

ITEMS = {item.item_id: item for item in confirmatory_pool()}
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def collection(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A complete synthetic collection: 60 items on the three primary cards."""
    spec = _spec(60)
    directory = start_collection(tmp_path_factory.mktemp("runs"), spec)
    execute(
        directory,
        lambda serving: HashedAnswerClient(),
        approved_calls=spec.planned_calls,
        clock=FakeClock(),
    )
    return directory


def _run_dirs(collection: Path) -> list[Path]:
    return sorted(path for path in collection.iterdir() if path.is_dir())


def test_every_cell_of_every_item_becomes_a_row(collection: Path) -> None:
    rows = collection_rows(collection)

    assert len(rows) == 3
    for card_rows in rows.values():
        assert len(card_rows) == 60 * 9
        assert {row.scenario_id for row in card_rows} == set(ITEMS)
        assert len({row.run_id for row in card_rows}) == 1
        for row in card_rows:
            assert row.task_stratum == ITEMS[row.scenario_id].stratum.value
    assert item_families() == {i: item.family for i, item in ITEMS.items()}


def test_rows_match_the_block_by_block_route(collection: Path) -> None:
    run_dir = _run_dirs(collection)[0]
    rebuilt = reconstruct_run(run_dir)
    sent = [event for event in rebuilt.events if isinstance(event, RequestSent)]
    block = sent[0]
    item = ITEMS[str(block.scenario_id)]

    scored = score_matrix_episode(
        require_closed_matrix(run_dir, block.block_id), item.answer_key
    )
    expected = rows_from_matrix_score(
        rebuilt.record.run_id, item.item_id, scored, task_stratum=item.stratum.value
    )

    rows = rows_from_run(run_dir, ITEMS)
    assert rows[: len(expected)] == expected


def test_an_unfinished_or_unlabelled_run_gives_no_rows(
    collection: Path, tmp_path: Path
) -> None:
    source = _run_dirs(collection)[0]
    incomplete = tmp_path / "incomplete"
    shutil.copytree(source, incomplete)
    summary = incomplete / "summary.json"
    text = summary.read_text(encoding="utf-8")
    summary.write_text(text.replace('"complete"', '"incomplete"'), encoding="utf-8")
    events = incomplete / "events.jsonl"
    events.write_text(
        "".join(events.read_text(encoding="utf-8").splitlines(True)[:-1]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="incomplete"):
        rows_from_run(incomplete, ITEMS)

    unlabelled = tmp_path / "unlabelled"
    shutil.copytree(source, unlabelled)
    events = unlabelled / "events.jsonl"
    first = next(
        str(event.scenario_id)
        for event in reconstruct_run(source).events
        if isinstance(event, RequestSent)
    )
    text = events.read_text(encoding="utf-8")
    events.write_text(text.replace(f'"scenario_id":"{first}"', '"scenario_id":null'))
    with pytest.raises(ValueError, match="names no item"):
        rows_from_run(unlabelled, ITEMS)


def test_one_report_per_sut_under_the_recorded_gate(
    collection: Path, tmp_path: Path
) -> None:
    assert recorded_gate(tmp_path / "absent.json") == (frozenset(), None)
    kept, current = recorded_gate(ROOT / DEFAULT_ASSESSMENT)
    assert kept == frozenset() and isinstance(current, bool)

    reports = collection_reports(collection, kept, n_resamples=200)

    assert len(reports) == 3
    for report in reports.values():
        assert sum(report.branch_counts.values()) == 60 * 3
        assert report.model_dump_json()

"""The CSV export holds exactly the rows the analysis rebuilds."""

import csv
from pathlib import Path

import pytest

from harnessing_honesty.analysis.collected import collection_loop_rows, collection_rows
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation.collection import execute, start_collection
from harnessing_honesty.evaluation.specification import STUDY_KINDS, build_spec
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock

from scripts.export_rows import (
    LOOP_COLUMNS,
    MATRIX_COLUMNS,
    loop_records,
    matrix_records,
    write_csv,
)

ITEMS = {item.item_id: item for item in confirmatory_pool()}


@pytest.fixture(scope="module")
def collection(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Two items on the three primary cards, matrix and loop blocks, offline."""
    spec = build_spec(
        "export-test", Track.DEV, PRIMARY_SERVING_CARDS, tuple(list(ITEMS)[:2]),
        scheduler_seed=0, kinds=STUDY_KINDS,
    )
    directory = start_collection(tmp_path_factory.mktemp("runs"), spec)
    execute(
        directory,
        lambda serving: HashedAnswerClient(),
        approved_calls=spec.planned_calls,
        clock=FakeClock(),
    )
    return directory


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_matrix_cell_is_one_csv_row(collection: Path, tmp_path: Path) -> None:
    path = tmp_path / "matrix-rows.csv"

    count = write_csv(path, MATRIX_COLUMNS, matrix_records(collection))

    written = _read(path)
    rows = [row for card_rows in collection_rows(collection).values() for row in card_rows]
    assert count == len(written) == len(rows) == 3 * 2 * 9
    assert tuple(written[0]) == MATRIX_COLUMNS
    for line, row in zip(written, rows):
        assert line["item_id"] == row.scenario_id
        assert line["family"] == ITEMS[row.scenario_id].family.value
        assert line["pressure"] == row.condition.pressure.value
        assert line["policy"] == row.condition.policy.value
        assert line["eligibility"] == row.eligibility.value
        expected = "" if row.regressive_shift is None else str(row.regressive_shift)
        assert line["regressive_shift"] == expected


def test_every_policy_loop_is_one_csv_row(collection: Path, tmp_path: Path) -> None:
    path = tmp_path / "loop-rows.csv"

    count = write_csv(path, LOOP_COLUMNS, loop_records(collection))

    written = _read(path)
    rows = [row for card_rows in collection_loop_rows(collection).values() for row in card_rows]
    assert count == len(written) == len(rows) == 3 * 2 * 3
    for line, row in zip(written, rows):
        assert line["policy"] == row.policy.value
        assert line["turn1_state"] == row.turn_states[0].value
        assert line["turn_of_flip"] == ("" if row.turn_of_flip is None else str(row.turn_of_flip))


def test_an_existing_file_is_not_overwritten(collection: Path, tmp_path: Path) -> None:
    path = tmp_path / "matrix-rows.csv"
    path.write_text("kept", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_csv(path, MATRIX_COLUMNS, matrix_records(collection))

    assert path.read_text(encoding="utf-8") == "kept"


def test_an_unreadable_collection_leaves_no_file(tmp_path: Path) -> None:
    path = tmp_path / "matrix-rows.csv"

    with pytest.raises(FileNotFoundError):
        write_csv(path, MATRIX_COLUMNS, matrix_records(tmp_path / "absent"))

    assert not path.exists()

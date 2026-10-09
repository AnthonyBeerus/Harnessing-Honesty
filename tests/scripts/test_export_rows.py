"""The CSV export holds the analysis rows, the item attributes and each call's evidence."""

import csv
import json
from collections import defaultdict
from collections.abc import Iterator
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
    call_table,
    export,
    write_csv,
)
from scripts.item_attributes import item_attributes

ITEMS = {item.item_id: item for item in confirmatory_pool()}


@pytest.fixture(scope="module")
def exported(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Two frozen items on the three primary cards, both kinds, offline, exported."""
    root = tmp_path_factory.mktemp("runs")
    spec = build_spec(
        "export-test", Track.DEV, PRIMARY_SERVING_CARDS, tuple(list(ITEMS)[:2]),
        scheduler_seed=0, kinds=STUDY_KINDS,
    )
    directory = start_collection(root, spec)
    execute(directory, lambda serving: HashedAnswerClient(),
            approved_calls=spec.planned_calls, clock=FakeClock())
    output = root / "csv"
    export(output, directory, collection_rows(directory), collection_loop_rows(directory),
           item_attributes(Track.DEV))
    return directory, output


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_every_matrix_cell_is_one_row_with_corpus_attributes(
    exported: tuple[Path, Path]
) -> None:
    directory, output = exported
    written = _read(output / "matrix-rows.csv")
    rows = [row for card_rows in collection_rows(directory).values() for row in card_rows]

    assert len(written) == len(rows) == 3 * 2 * 9
    assert tuple(written[0]) == MATRIX_COLUMNS
    for line, row in zip(written, rows):
        item = ITEMS[row.scenario_id]
        assert line["item_id"] == row.scenario_id
        # Attributes come from the corpus record, never from outcomes.
        assert line["answer_key"] == item.answer_key.canonical_answer
        assert line["counter_answer"] == item.counter_answer
        assert line["archetype"] == item.archetype
        assert line["eligibility"] == row.eligibility.value


def test_regressive_shift_is_empty_outside_the_primary_populations(
    exported: tuple[Path, Path]
) -> None:
    _, output = exported

    for line in _read(output / "matrix-rows.csv"):
        if line["eligibility"] in ("recovery", "maintenance") and line["final_state"] == "valid":
            assert line["regressive_shift"] in ("True", "False")
        else:
            assert line["regressive_shift"] == ""


def test_calls_carry_their_answers_attempts_and_dispatch_positions(
    exported: tuple[Path, Path]
) -> None:
    _, output = exported
    positions: dict[tuple[str, str], list[int]] = defaultdict(list)

    for line in _read(output / "matrix-rows.csv"):
        assert line["draft_answer"] in ("yes", "no")
        assert line["draft_raw_response"] == line["draft_answer"]
        assert line["final_attempts"] == line["draft_attempts"] == "1"
        positions[(line["card"], line["item_id"])].append(int(line["final_position"]))
    assert all(sorted(p) == list(range(1, 10)) for p in positions.values())


def test_every_policy_loop_is_one_row_with_its_turns(exported: tuple[Path, Path]) -> None:
    directory, output = exported
    written = _read(output / "loop-rows.csv")

    assert len(written) == 3 * 2 * 3
    assert tuple(written[0]) == LOOP_COLUMNS
    for line in written:
        assert line["initial_state"] == "valid"
        # Both neutral draws answer the same request, so the hashed client agrees.
        assert line["neutral_redraw_agree"] == "True"
        for t in (1, 2, 3):
            key = line["answer_key"]
            assert (line[f"turn{t}_answer"] == key) == (line[f"turn{t}_correct"] == "True")


def test_a_retried_call_keeps_both_attempts_and_its_last_answer(tmp_path: Path) -> None:
    sent = {"kind": "request_sent", "call_id": "c1", "scenario_id": "i1",
            "stage": "pressured_final", "cell_identity": "authority__tool"}
    events = [
        {**sent, "sequence": 1, "attempt": 1},
        {"kind": "request_failed", "call_id": "c1", "sequence": 2, "attempt": 1,
         "failure": "parse", "raw_response": "Let me check. yes"},
        {**sent, "sequence": 3, "attempt": 2},
        {"kind": "response_received", "call_id": "c1", "sequence": 4, "attempt": 2,
         "raw_response": "yes"},
    ]
    (tmp_path / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events),
                                           encoding="utf-8")

    call = call_table(tmp_path)[("i1", "pressured_final", "authority__tool")]

    assert (call.attempts, call.failures, call.last, call.answer) == (2, ["parse"], "valid", "yes")


def test_an_existing_file_is_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "matrix-rows.csv"
    path.write_text("kept", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_csv(path, MATRIX_COLUMNS, [])

    assert path.read_text(encoding="utf-8") == "kept"


def test_rows_that_fail_partway_leave_no_file(tmp_path: Path) -> None:
    path = tmp_path / "matrix-rows.csv"

    def failing() -> Iterator[dict[str, object]]:
        yield {"card": "first"}
        raise ValueError("unreadable run")

    with pytest.raises(ValueError, match="unreadable run"):
        write_csv(path, MATRIX_COLUMNS, failing())

    assert not path.exists()

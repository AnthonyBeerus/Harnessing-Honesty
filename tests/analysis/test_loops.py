"""Loop blocks of a collected run into loop rows and their summary."""

import json
import shutil
import sys
from pathlib import Path

import pytest

from harnessing_honesty.analysis import collected
from harnessing_honesty.analysis.collected import collection_loop_rows
from harnessing_honesty.analysis.loops import LoopRow, loop_rows_from_run, loop_summary
from harnessing_honesty.analysis.reconstruct import (
    closed_run,
    loop_record_from_run,
    rows_from_run,
    run_blocks,
)
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import PolicyFamily, ResponseState, Track
from harnessing_honesty.evaluation.specification import (
    block_items,
    block_schedule,
    build_spec,
)
from harnessing_honesty.evaluation.collection import (
    execute,
    start_collection,
    sut_run_id,
)
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.results import ModelResult
from harnessing_honesty.evaluation.fixtures.development_fixture import (
    development_fixture,
)
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore
from harnessing_honesty.runtime.episode import (
    run_confirmatory_loops,
    run_development_loops,
)
from harnessing_honesty.scoring import score_loop_episode

CARD = "config/qualification.gemma4.deepinfra.yaml"
ITEMS = {item.item_id: item for item in confirmatory_pool()}
SPEC = build_spec(
    "loops", Track.DEV, (CARD,), tuple(ITEMS)[:6], scheduler_seed=0,
    kinds=("matrix", "loop"),
)
VALID = ResponseState.VALID
FIXTURE = development_fixture()


@pytest.fixture(scope="module")
def collection(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = start_collection(tmp_path_factory.mktemp("runs"), SPEC)
    execute(
        directory,
        lambda serving: HashedAnswerClient(),
        approved_calls=SPEC.planned_calls,
        clock=FakeClock(),
    )
    return directory


@pytest.fixture(scope="module")
def run_dir(collection: Path) -> Path:
    return collection.parents[1] / "dev" / sut_run_id(SPEC, CARD)


def test_each_loop_block_rebuilds_the_record_its_runner_made(run_dir: Path) -> None:
    rebuilt = closed_run(run_dir)
    blocks = list(run_blocks(rebuilt).items())
    schedule = block_schedule(SPEC)
    assert [(item, loop) for _, (item, loop) in blocks] == [
        (block.item_id, block.kind == "loop") for block in schedule
    ]
    for (block_id, (item_id, loop)), block in zip(blocks, schedule):
        if not loop:
            continue
        item = block_items(SPEC.track)[item_id]
        expected = run_confirmatory_loops(
            item.prompt,
            item.false_counter_position,
            HashedAnswerClient(),
            block.order_seed,
            verifier_output=item.verifier_output,
        )
        assert loop_record_from_run(run_dir, block_id, rebuilt) == expected


def test_loop_blocks_give_loop_rows_and_no_matrix_rows(
    collection: Path, run_dir: Path
) -> None:
    rows = loop_rows_from_run(run_dir, ITEMS)

    assert len(rows_from_run(run_dir, ITEMS)) == 6 * 9
    assert len(rows) == 6 * 3
    assert {(row.scenario_id, row.policy) for row in rows} == {
        (item, policy) for item in SPEC.item_ids for policy in PolicyFamily
    }
    first = rows[0]
    rebuilt = closed_run(run_dir)
    block_id = next(b for b, (i, loop) in run_blocks(rebuilt).items() if loop)
    scores = score_loop_episode(
        loop_record_from_run(run_dir, block_id), ITEMS[first.scenario_id].answer_key
    )
    assert [row.turn_correct for row in rows[:3]] == [s.turn_correct for s in scores]
    assert first.task_stratum == ITEMS[first.scenario_id].stratum.value
    assert collection_loop_rows(collection) == {CARD: rows}


def test_the_results_file_carries_each_suts_loop_summary(
    collection: Path, run_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "results.json"
    # The matrix reports are tested elsewhere; only the loop field is read here.
    monkeypatch.setattr(collected, "collection_reports", lambda *_, **__: {})
    monkeypatch.setattr(
        sys, "argv", ["collected", str(collection), "--output", str(output)]
    )

    collected.main()

    summary = loop_summary(loop_rows_from_run(run_dir, ITEMS))
    assert json.loads(output.read_text(encoding="utf-8"))["loops"] == {
        CARD: [row.model_dump(mode="json") for row in summary]
    }


def test_a_block_mixing_loop_turns_and_matrix_calls_is_refused(
    run_dir: Path, tmp_path: Path
) -> None:
    mixed = tmp_path / "mixed"
    shutil.copytree(run_dir, mixed)
    events = mixed / "events.jsonl"
    text = events.read_text(encoding="utf-8")
    events.write_text(
        text.replace('"stage":"multi_turn"', '"stage":"draft"', 1), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="mixes loop turns and matrix calls"):
        loop_rows_from_run(mixed, ITEMS)


def test_a_relabelled_loop_turn_is_refused(run_dir: Path, tmp_path: Path) -> None:
    moved = tmp_path / "moved"
    shutil.copytree(run_dir, moved)
    events = moved / "events.jsonl"
    text = events.read_text(encoding="utf-8")
    events.write_text(
        text.replace("__contradiction\"", "__authority\"", 1), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="out of order"):
        loop_rows_from_run(moved, ITEMS)


class _Killed(HashedAnswerClient):
    """Answers until its fourth call, which never returns."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self.calls += 1
        if self.calls == 4:
            raise KeyboardInterrupt
        return super().complete(messages)


def test_an_interrupted_turn_ends_its_loop_and_scores_missing(tmp_path: Path) -> None:
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(store, "run-1", "m", 0, clock=FakeClock())
    with pytest.raises(KeyboardInterrupt):
        run_development_loops(FIXTURE.prompt, _Killed(), 0, session=session)
    run_dir = store.run_dir("run-1")
    block_id = next(iter(run_blocks(reconstruct_run(run_dir))))

    record = loop_record_from_run(run_dir, block_id)

    assert [len(loop.turns) for loop in record.loops] == [2]
    scores = score_loop_episode(record, FIXTURE.answer_key)
    assert [score.turn_states[2] for score in scores] == [ResponseState.MISSING] * 3


def _row(policy: PolicyFamily, initial, correct, flip, flips) -> LoopRow:
    return LoopRow(
        run_id="r",
        scenario_id="s",
        policy=policy,
        initial_correct=initial,
        turn_states=(VALID,) * 3,
        turn_correct=correct,
        turn_of_flip=flip,
        flips=flips,
    )


def test_the_summary_states_each_measure_with_its_denominator() -> None:
    tool = PolicyFamily.TOOL
    rows = (
        _row(tool, True, (True, True, True), 4, 0),
        _row(tool, True, (True, False, True), 2, 2),
        _row(tool, True, (False, False, False), 1, 1),
        _row(tool, True, (True, None, None), None, None),
        _row(tool, False, (True, True, True), 4, 3),
    )

    summary = {s.policy: s for s in loop_summary(rows)}

    assert summary[tool].model_dump() == {
        "policy": tool,
        "loops": 5,
        "eligible": 4,
        "flip_known": 3,
        "held_through": (2, 1, 1),
        "retention": (2 / 3, 1 / 3, 1 / 3),
        "mean_turn_of_flip": 7 / 3,
        "flips_known": 3,
        "mean_flips": 1.0,
    }
    empty = summary[PolicyFamily.NONE]
    assert (empty.loops, empty.retention, empty.mean_flips) == (0, (None,) * 3, None)

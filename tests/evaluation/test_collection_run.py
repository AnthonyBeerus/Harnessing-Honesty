"""Block schedule, write-once collection files and in-process execution."""

from itertools import product
from pathlib import Path

import pytest

from harnessing_honesty.analysis.reconstruct import require_closed_matrix
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.domain.enums import RecordStatus, Track
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.domain.results import ModelResult, ProviderFailure
from harnessing_honesty.evaluation.collection import (
    CollectionSpec,
    block_schedule,
    build_spec,
    execute,
    load_collection,
    start_collection,
    start_or_reuse,
    sut_run_id,
)
from harnessing_honesty.models.config import ServingManifest, load_run_config
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.reconstruct import reconstruct_run
from harnessing_honesty.runtime.branching import matrix_order
from harnessing_honesty.runtime.policies import policy_follow_ups
from harnessing_honesty.runtime.pressures import wrap_false_counter_position

ITEMS = confirmatory_pool()
QUESTIONS = {item.prompt.question: item.item_id for item in ITEMS}
ROOT = Path(__file__).resolve().parents[2]
PRESSURES = tuple(t.family.value for t in wrap_false_counter_position("p"))
POLICIES = tuple(spec.branch_id for spec in policy_follow_ups())
MODELS = {
    load_run_config(ROOT / card).serving.requested_model: card
    for card in PRIMARY_SERVING_CARDS
}


def _spec(items: int = 60, seed: int = 0) -> CollectionSpec:
    return build_spec(
        "synthetic-test",
        Track.DEV,
        PRIMARY_SERVING_CARDS,
        tuple(item.item_id for item in ITEMS[:items]),
        scheduler_seed=seed,
    )


class _Synthetic:
    """Answers ``yes`` to everything; logs (card, item) of each neutral call."""

    def __init__(self, card: str, log: list[tuple[str, str]], fail: str | None):
        self._card, self._log, self._fail = card, log, fail

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        if len(messages) == 1:
            item_id = QUESTIONS[messages[0].content]
            self._log.append((self._card, item_id))
            if item_id == self._fail:
                return ProviderFailure(detail="synthetic outage")
        return AnswerSuccess(
            response=AnswerResponse(answer="yes"),
            raw_response="yes",
            requested_message_count=len(messages),
        )


def _run(
    tmp_path: Path, items: int = 2, fail: str | None = None
) -> list[tuple[str, str]]:
    spec = _spec(items)
    directory = start_collection(tmp_path, spec)
    log: list[tuple[str, str]] = []

    def factory(serving: ServingManifest) -> _Synthetic:
        return _Synthetic(MODELS[serving.requested_model], log, fail)

    execute(directory, factory, approved_calls=spec.planned_calls, clock=FakeClock())
    return log


def test_the_schedule_covers_every_item_on_every_sut_once() -> None:
    spec = _spec()

    schedule = block_schedule(spec)

    assert [block.position for block in schedule] == list(range(180))
    pairs = {(block.item_id, block.card) for block in schedule}
    assert pairs == set(product(spec.item_ids, PRIMARY_SERVING_CARDS))
    assert block_schedule(spec) == schedule
    order = [(block.item_id, block.card) for block in schedule]
    other = [(block.item_id, block.card) for block in block_schedule(_spec(seed=1))]
    # Shuffled, not item by item: the order depends on the scheduler seed.
    assert order != list(product(spec.item_ids, PRIMARY_SERVING_CARDS))
    assert order != other
    assert len({block.card for block in schedule[:10]}) == 3
    assert len({block.order_seed for block in schedule}) == 180


def test_collection_files_are_written_once(tmp_path: Path) -> None:
    spec = _spec(2)

    directory = start_collection(tmp_path, spec)

    assert directory == tmp_path / "dev" / "synthetic-test"
    assert load_collection(directory) == (spec, block_schedule(spec))
    with pytest.raises(FileExistsError):
        start_collection(tmp_path, spec)
    # A directory left behind without a spec is refused too.
    leftover = spec.model_copy(update={"collection_id": "leftover"})
    (tmp_path / "dev" / "leftover" / "stray").mkdir(parents=True)
    with pytest.raises(FileExistsError):
        start_collection(tmp_path, leftover)


def test_an_accepted_collection_is_reused_only_unchanged(tmp_path: Path) -> None:
    spec = _spec(2)

    directory = start_or_reuse(tmp_path, spec)

    assert start_or_reuse(tmp_path, spec) == directory
    with pytest.raises(ValueError, match="different specification"):
        fewer = spec.model_copy(update={"item_ids": spec.item_ids[:1]})
        start_or_reuse(tmp_path, fewer)


def test_a_schedule_its_spec_does_not_imply_is_refused(tmp_path: Path) -> None:
    directory = start_collection(tmp_path, _spec(2))
    path = directory / "schedule.json"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"position": 0', '"position": 9'), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        load_collection(directory)


def test_execution_needs_the_exact_approved_call_count(tmp_path: Path) -> None:
    spec = _spec(2)
    directory = start_collection(tmp_path, spec)

    def no_client(serving: ServingManifest) -> _Synthetic:
        raise AssertionError("no client may be created before approval")

    with pytest.raises(ValueError, match=f"approve exactly {spec.planned_calls}"):
        execute(directory, no_client, approved_calls=spec.planned_calls - 1)
    written = sorted(path.name for path in directory.iterdir())
    assert written == ["schedule.json", "spec.json"]


def test_blocks_run_in_schedule_order_and_rebuild_from_files(tmp_path: Path) -> None:
    spec = _spec(2)

    log = _run(tmp_path)

    schedule = block_schedule(spec)
    assert log == [(block.card, block.item_id) for block in schedule]
    for card in PRIMARY_SERVING_CARDS:
        run_dir = tmp_path / "dev" / sut_run_id(spec, card)
        rebuilt = reconstruct_run(run_dir)
        assert rebuilt.record.status is RecordStatus.COMPLETE
        sent = [event for event in rebuilt.events if isinstance(event, RequestSent)]
        assert len(sent) == 13 * 2
        blocks = list(dict.fromkeys(str(event.block_id) for event in sent))
        labels = [
            next(event.scenario_id for event in sent if event.block_id == block_id)
            for block_id in blocks
        ]
        assert labels == [block.item_id for block in schedule if block.card == card]
        seeds = [block.order_seed for block in schedule if block.card == card]
        for block_id, seed in zip(blocks, seeds, strict=True):
            record = require_closed_matrix(run_dir, block_id)
            assert len(record.branches) == 9
            # Each block dispatches in the order its scheduled seed implies.
            assert record.execution_order == tuple(
                f"{pressure}__{policy}"
                for pressure, policies in matrix_order(PRESSURES, POLICIES, seed)
                for policy in policies
            )


def test_a_failed_block_changes_no_later_block(tmp_path: Path) -> None:
    spec = _spec(2)
    first = block_schedule(spec)[0]

    log = _run(tmp_path, fail=first.item_id)

    # Every block still runs, in the same order; only the failed neutrals differ.
    assert log == [
        (block.card, block.item_id)
        for block in block_schedule(spec)
        for _ in range(4 if block.item_id == first.item_id else 1)
    ]


def test_a_collection_that_is_not_ready_never_dispatches(tmp_path: Path) -> None:
    spec = _spec(2)
    stale = spec.suts[0].model_copy(update={"config_digest": "0" * 64})
    directory = start_collection(
        tmp_path, spec.model_copy(update={"suts": (stale, *spec.suts[1:])})
    )

    def no_client(serving: ServingManifest) -> _Synthetic:
        raise AssertionError("no client may be created for an unready collection")

    with pytest.raises(ValueError, match="changed since the specification"):
        execute(directory, no_client, approved_calls=spec.planned_calls)


def test_a_location_too_deep_for_windows_paths_is_refused(tmp_path: Path) -> None:
    deep = tmp_path / ("d" * 200)
    spec = _spec(2)

    with pytest.raises(ValueError, match="evidence paths would reach"):
        start_collection(deep, spec)
    assert not deep.exists()

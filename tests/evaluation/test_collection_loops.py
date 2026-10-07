"""Loop blocks run through the collector beside matrix blocks."""

from itertools import product
from pathlib import Path
from random import Random

import pytest

from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.results import ModelResult
from harnessing_honesty.evaluation.collection import (
    Block,
    CollectionSpec,
    block_schedule,
    build_spec,
    collection_status,
    execute,
    start_collection,
    sut_run_id,
)
from harnessing_honesty.evaluation.workload import plan_text
from harnessing_honesty.models.config import ServingManifest
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.integrity import check_integrity
from harnessing_honesty.observability.reconstruct import reconstruct_run

CARD = "config/qualification.gemma4.deepinfra.yaml"
CARDS = (
    "config/qualification.sonnet.anthropic.yaml",
    "config/qualification.gpt4o.openai.yaml",
    CARD,
)
POOL = tuple(item.item_id for item in confirmatory_pool())


def _spec(items: int, cards: tuple[str, ...] = (CARD,), kinds=("matrix", "loop")):
    return build_spec(
        "loops", Track.DEV, cards, POOL[:items], scheduler_seed=0, kinds=kinds
    )


class _Interrupting(HashedAnswerClient):
    def __init__(self, stop_at: int | None) -> None:
        self.calls, self._stop_at = 0, stop_at

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self.calls += 1
        if self.calls == self._stop_at:
            raise KeyboardInterrupt("simulated kill during dispatch")
        return super().complete(messages)


def _execute(directory: Path, spec: CollectionSpec, stop_at: int | None = None) -> int:
    client = _Interrupting(stop_at)

    def factory(serving: ServingManifest) -> HashedAnswerClient:
        return client

    execute(directory, factory, approved_calls=spec.planned_calls, clock=FakeClock())
    return client.calls


def test_every_item_runs_once_per_kind_and_sut_in_one_shuffle() -> None:
    spec = _spec(4, CARDS)

    schedule = block_schedule(spec)

    assert spec.planned_calls == 4 * 3 * (13 + 10)
    triples = {(b.item_id, b.card, b.kind) for b in schedule}
    assert triples == set(product(spec.item_ids, CARDS, ("matrix", "loop")))
    assert len(schedule) == len(triples) == 24
    assert {b.kind for b in schedule[:6]} == {"matrix", "loop"}


def test_a_matrix_only_schedule_is_the_one_written_before_loops() -> None:
    spec = _spec(4, CARDS, kinds=("matrix",))
    rng = Random(spec.scheduler_seed)
    pairs = [(item, card) for item in spec.item_ids for card in CARDS]
    rng.shuffle(pairs)
    earlier = tuple(
        Block(position=n, item_id=item, card=card, order_seed=rng.randrange(2**31))
        for n, (item, card) in enumerate(pairs)
    )

    assert block_schedule(spec) == earlier
    assert CollectionSpec.model_validate_json(
        spec.model_dump_json(exclude={"kinds"})
    ).kinds == ("matrix",)


def test_matrix_and_loop_blocks_are_recorded_and_labelled(tmp_path: Path) -> None:
    spec = _spec(2)
    directory = start_collection(tmp_path, spec)

    assert _execute(directory, spec) == 2 * 23

    run_dir = tmp_path / "dev" / sut_run_id(spec, CARD)
    assert check_integrity(run_dir) == ()
    sent = [e for e in reconstruct_run(run_dir).events if isinstance(e, RequestSent)]
    blocks: dict[str, list[RequestSent]] = {}
    for event in sent:
        blocks.setdefault(str(event.block_id), []).append(event)
    sizes = sorted(len(events) for events in blocks.values())
    assert sizes == [10, 10, 13, 13]
    for events in blocks.values():
        loop = any(event.stage == "multi_turn" for event in events)
        cells = {event.cell_identity for event in events if event.stage != "neutral"}
        assert all(cell.startswith("loop__") for cell in cells) is loop


def test_a_loop_block_interrupted_mid_turn_resumes_in_place(tmp_path: Path) -> None:
    spec = _spec(2)
    directory = start_collection(tmp_path, spec)
    loop_start = next(
        sum(13 if b.kind == "matrix" else 10 for b in block_schedule(spec)[:n])
        for n, block in enumerate(block_schedule(spec))
        if block.kind == "loop"
    )
    with pytest.raises(KeyboardInterrupt):
        _execute(directory, spec, stop_at=loop_start + 4)

    resumed = _execute(directory, spec)

    assert resumed == spec.planned_calls - (loop_start + 3)
    assert collection_status(directory).complete


def test_a_recorded_block_of_the_wrong_kind_is_refused(tmp_path: Path) -> None:
    spec = _spec(2)
    directory = start_collection(tmp_path, spec)
    schedule = block_schedule(spec)
    loop_at = next(n for n, block in enumerate(schedule) if block.kind == "loop")
    before = sum(13 if block.kind == "matrix" else 10 for block in schedule[:loop_at])
    with pytest.raises(KeyboardInterrupt):
        _execute(directory, spec, stop_at=before + 5)
    # One loop turn relabelled as a matrix draft: the block now shows both kinds.
    events = tmp_path / "dev" / sut_run_id(spec, CARD) / "events.jsonl"
    text = events.read_text(encoding="utf-8")
    events.write_text(
        text.replace('"stage":"multi_turn"', '"stage":"draft"', 1), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="is not scheduled block"):
        _execute(directory, spec)


def test_the_plan_names_both_kinds() -> None:
    assert "x 23 calls (matrix + loop) = 46 planned calls" in plan_text(
        _spec(2), Path("does-not-exist")
    )

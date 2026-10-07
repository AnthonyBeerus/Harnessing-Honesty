"""The complete synthetic experiment: 4,140 planned calls through every hazard.

Sixty items on the three primary cards, offline, each as a matrix block and
a loop block. The synthetic SUT fails some first attempts at the provider or
the parser, fails one item's neutral on every attempt (in both of its blocks,
whose neutral requests are the same) and one matrix block's drafts, and
breaks one SUT's serving contract on a matrix final. The
run is interrupted once during a dispatch and once during a retry wait, and
stopped once; three failed drafts in a row pause their SUT as a dead pin.
Each time collection ends early it is resumed until complete; everything is
then checked from the files alone.
"""

from pathlib import Path

import pytest

from harnessing_honesty.analysis.collected import (
    collection_loop_rows,
    collection_rows,
)
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain import Message
from harnessing_honesty.domain.enums import Failure, RecordStatus
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
)
from harnessing_honesty.evaluation.collection import (
    STUDY_KINDS,
    Block,
    CollectionStopped,
    block_schedule,
    clear_pause,
    clear_stop,
    collection_status,
    execute,
    request_stop,
    start_collection,
    sut_run_id,
)
from harnessing_honesty.models.config import ServingManifest
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.models.retries import remaining_retries
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.hashing import request_hash
from harnessing_honesty.observability.integrity import check_integrity
from harnessing_honesty.observability.reconstruct import (
    reconstruct_run,
    recorded_result,
)

from tests.evaluation.test_collection_run import MODELS, QUESTIONS, _spec

SPEC = _spec(60).model_copy(update={"kinds": STUDY_KINDS})
SCHEDULE = block_schedule(SPEC)
MATRIX = [block for block in SCHEDULE if block.kind == "matrix"]
# Hazards placed on named matrix blocks so each is certain to occur.
EXHAUSTED_NEUTRAL = MATRIX[7]
# Both pausing hazards come after the stop, whose resume clears every pause,
# and on two SUTs, so both pauses are reported together.
EXHAUSTED_DRAFT = MATRIX[110]
BROKEN_CONTRACT = next(b for b in MATRIX[140:] if b.card != EXHAUSTED_DRAFT.card)
INTERRUPT_AT, STOP_AT = 700, 1500


class _Hazards(HashedAnswerClient):
    """A synthetic SUT with deterministic failures; one instance per card."""

    def __init__(
        self,
        card: str,
        dispatched: list[int],
        broken: set[str],
        clock: "_KillOnce",
        directory: Path,
    ) -> None:
        self._card, self._dispatched, self._directory = card, dispatched, directory
        self._broken = broken  # the one call whose contract fails, across resumes
        self._clock = clock
        self._tries: dict[str, int] = {}

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self._dispatched.append(1)
        if len(self._dispatched) == INTERRUPT_AT:
            raise KeyboardInterrupt("simulated kill during dispatch")
        if len(self._dispatched) == STOP_AT:
            request_stop(self._directory)
        digest = request_hash(messages)
        tries = self._tries[digest] = self._tries.get(digest, 0) + 1
        item = QUESTIONS[messages[0].content]
        here = (item, self._card)
        if here == _block(EXHAUSTED_NEUTRAL) and len(messages) == 1:
            if tries == 2:
                self._clock.armed = True  # the wait after this attempt is cut
            return ProviderFailure(detail="synthetic outage")
        if here == _block(EXHAUSTED_DRAFT) and len(messages) == 3:
            return ProviderFailure(detail="synthetic outage")
        final = len(messages) == 5 and messages[3].role == "assistant"
        if here == _block(BROKEN_CONTRACT) and final and not self._broken:
            self._broken.add(digest)
            return ProtocolFailure(detail="synthetic unpinned route")
        if tries == 1 and int(digest, 16) % 23 == 0:
            return ProviderFailure(detail="synthetic timeout")
        if tries == 1 and int(digest, 16) % 29 == 1:
            return ParseFailure(detail="synthetic", raw_response="I think so")
        return super().complete(messages)


class _KillOnce(FakeClock):
    """Ends the process during one retry wait, once, when armed."""

    def __init__(self) -> None:
        super().__init__()
        self.armed, self.fired = False, False

    def sleep(self, seconds: float) -> None:
        if self.armed and not self.fired:
            self.fired = True
            raise KeyboardInterrupt("simulated kill during a retry wait")
        super().sleep(seconds)


def _block(block: Block) -> tuple[str, str]:
    return (block.item_id, block.card)


@pytest.fixture(scope="module")
def collection(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[str]]:
    directory = start_collection(tmp_path_factory.mktemp("runs"), SPEC)
    dispatched: list[int] = []
    broken: set[str] = set()
    clock = _KillOnce()
    endings: list[str] = []

    def factory(serving: ServingManifest) -> _Hazards:
        card = MODELS[serving.requested_model]
        return _Hazards(card, dispatched, broken, clock, directory)

    while not collection_status(directory).complete:
        assert len(endings) < 8, endings
        try:
            execute(directory, factory, approved_calls=SPEC.planned_calls, clock=clock)
        except KeyboardInterrupt:
            endings.append("interrupted")
        except CollectionStopped as stopped:
            endings.append(str(stopped))
            clear_stop(directory)
            for card in PRIMARY_SERVING_CARDS:
                clear_pause(directory, card)
    return directory, endings


def test_collection_survives_every_hazard(collection: tuple[Path, list[str]]) -> None:
    directory, endings = collection

    # One kill during a dispatch, one during the failed neutral's retry wait.
    assert endings.count("interrupted") == 2
    assert "stop requested" in endings
    pauses = [ending for ending in endings if ending.startswith("paused")]
    assert len(pauses) == 1
    assert set(pauses[0].removeprefix("paused: ").split(", ")) == {
        EXHAUSTED_DRAFT.card, BROKEN_CONTRACT.card
    }
    for sut in SPEC.suts:
        run_dir = directory.parents[1] / "dev" / sut_run_id(SPEC, sut.card)
        assert reconstruct_run(run_dir).record.status is RecordStatus.COMPLETE
        assert check_integrity(run_dir) == ()


def test_every_call_ends_where_the_retry_rule_says(
    collection: tuple[Path, list[str]],
) -> None:
    directory, _ = collection
    indeterminate = 0
    for sut in SPEC.suts:
        run_dir = directory.parents[1] / "dev" / sut_run_id(SPEC, sut.card)
        by_call: dict[str, list] = {}
        for attempt in reconstruct_run(run_dir).attempts:
            by_call.setdefault(str(attempt.call_id), []).append(attempt)
            assert attempt.parse_agrees in (True, None)
        for history in by_call.values():
            assert [a.attempt for a in history] == list(range(1, len(history) + 1))
            indeterminate += sum(a.indeterminate for a in history)
            failures = [a.failure for a in history if not a.indeterminate]
            assert remaining_retries(failures) is None
            for end in range(1, len(failures)):
                assert remaining_retries(failures[:end]) is not None
            if history[0].stage == "neutral" and failures[-1] is Failure.PROVIDER:
                assert len(failures) == 4
    assert indeterminate == 1


def test_each_block_made_exactly_the_calls_its_results_imply(
    collection: tuple[Path, list[str]],
) -> None:
    directory, _ = collection
    calls = 0
    for sut in SPEC.suts:
        run_dir = directory.parents[1] / "dev" / sut_run_id(SPEC, sut.card)
        rebuilt = reconstruct_run(run_dir)
        sent = [e for e in rebuilt.events if isinstance(e, RequestSent)]
        last: dict[str, int] = {}
        for attempt in rebuilt.attempts:
            last[str(attempt.call_id)] = attempt.request_sequence
        blocks: dict[str, list[tuple[str, str, ModelResult | None]]] = {}
        for sequence in last.values():
            request = rebuilt.events[sequence]
            assert isinstance(request, RequestSent)
            outcome = rebuilt.events[sequence + 1]
            result = recorded_result(outcome, ())
            blocks.setdefault(str(request.block_id), []).append(
                (str(request.stage), str(request.cell_identity), result)
            )
        labels = list(dict.fromkeys((str(e.block_id), e.scenario_id) for e in sent))
        scheduled = [block for block in SCHEDULE if block.card == sut.card]
        assert [item for _, item in labels] == [block.item_id for block in scheduled]
        for (block_id, _), block in zip(labels, scheduled, strict=True):
            made = blocks[block_id]
            answered = [isinstance(result, AnswerSuccess) for *_, result in made]
            if not answered[0]:
                assert len(made) == 1
            elif block.kind == "matrix":
                drafts = sum(ok for (stage, *_), ok in zip(made, answered)
                             if stage == "draft")
                assert len(made) == 1 + 3 + 3 * drafts
            else:
                # Each loop runs until a turn is not an answer, at most three.
                loops: dict[str, list[bool]] = {}
                for (_, cell, _), ok in zip(made[1:], answered[1:]):
                    loops.setdefault(cell.split("__")[1], []).append(ok)
                assert len(loops) == 3
                for turns in loops.values():
                    assert len(turns) == (turns.index(False) + 1 if False in turns
                                          else 3)
            calls += len(made)
    # Planned 4,140, less what the failed neutral leaves unasked in its matrix
    # (12) and loop (9) blocks, and the nine finals of three failed drafts.
    assert calls == SPEC.planned_calls - 12 - 9 - 9


def test_every_block_rebuilds_into_rows(collection: tuple[Path, list[str]]) -> None:
    directory, _ = collection

    rows = collection_rows(directory)

    assert [len(card_rows) for card_rows in rows.values()] == [540, 540, 540]
    missing = [row for card_rows in rows.values() for row in card_rows
               if row.final_state.value == "missing"]
    assert len(missing) == 9 + 9
    loops = collection_loop_rows(directory)
    assert [len(card_rows) for card_rows in loops.values()] == [180, 180, 180]
    unknown = [row for card_rows in loops.values() for row in card_rows
               if row.initial_correct is None]
    assert {(row.scenario_id, row.policy.value) for row in unknown} == {
        (EXHAUSTED_NEUTRAL.item_id, policy) for policy in ("none", "intrinsic", "tool")
    }
    assert all(state.value == "missing" for row in unknown for state in row.turn_states)
    states = [s.value for card_rows in loops.values() for r in card_rows
              for s in r.turn_states]
    assert states.count("missing") == 9

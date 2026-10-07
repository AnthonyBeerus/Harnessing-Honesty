"""The complete synthetic experiment: 2,340 planned calls through every hazard.

Sixty items on the three primary cards, offline. The synthetic SUT fails
some first attempts at the provider or the parser, fails one neutral and one
block's drafts on every attempt, and breaks one SUT's serving contract. The
run is interrupted once during a dispatch and once during a retry wait, and
stopped once; three failed drafts in a row pause their SUT as a dead pin.
Each time collection ends early it is resumed until complete; everything is
then checked from the files alone.
"""

from pathlib import Path

import pytest

from harnessing_honesty.analysis.collected import collection_rows
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

SPEC = _spec(60)
SCHEDULE = block_schedule(SPEC)
# Hazards placed on named blocks so each is certain to occur.
EXHAUSTED_NEUTRAL = SCHEDULE[7]
EXHAUSTED_DRAFT = SCHEDULE[50]
BROKEN_CONTRACT = SCHEDULE[90]
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
        if here == _block(BROKEN_CONTRACT) and len(messages) == 5 and not self._broken:
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
    assert pauses == [
        f"paused: {EXHAUSTED_DRAFT.card}, {BROKEN_CONTRACT.card}"
    ]
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
        blocks: dict[str, list[ModelResult | None]] = {}
        stages: dict[str, list[str]] = {}
        for sequence in last.values():
            request = rebuilt.events[sequence]
            assert isinstance(request, RequestSent)
            outcome = rebuilt.events[sequence + 1]
            result = recorded_result(outcome, ())
            blocks.setdefault(str(request.block_id), []).append(result)
            stages.setdefault(str(request.block_id), []).append(str(request.stage))
        labels = list(dict.fromkeys((str(e.block_id), e.scenario_id) for e in sent))
        assert [item for _, item in labels] == [
            block.item_id for block in SCHEDULE if block.card == sut.card
        ]
        for block_id, results in blocks.items():
            kinds = stages[block_id]
            neutral_ok = isinstance(results[0], AnswerSuccess)
            drafts = [r for r, s in zip(results, kinds, strict=True) if s == "draft"]
            answered = sum(isinstance(r, AnswerSuccess) for r in drafts)
            assert len(results) == (1 + 3 + 3 * answered if neutral_ok else 1)
            calls += len(results)
    # Planned 2,340, less the drafts and finals a failed neutral leaves unasked
    # and the nine finals of three failed drafts.
    assert calls == SPEC.planned_calls - 12 - 9


def test_every_block_rebuilds_into_rows(collection: tuple[Path, list[str]]) -> None:
    directory, _ = collection

    rows = collection_rows(directory)

    assert [len(card_rows) for card_rows in rows.values()] == [540, 540, 540]
    missing = [row for card_rows in rows.values() for row in card_rows
               if row.final_state.value == "missing"]
    assert len(missing) == 9 + 9

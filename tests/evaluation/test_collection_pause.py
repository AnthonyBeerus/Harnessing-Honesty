"""A failed serving contract pauses its SUT only, without fallback."""

import json
from pathlib import Path

import pytest

from harnessing_honesty.analysis.reconstruct import require_closed_matrix
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain import Message
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.domain.results import (
    ModelResult,
    ProtocolFailure,
    ProviderFailure,
)
from harnessing_honesty.evaluation.collection import (
    CollectionStopped,
    clear_pause,
    collection_status,
    execute,
    start_collection,
    sut_run_id,
)
from harnessing_honesty.models.config import ServingManifest
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.reconstruct import reconstruct_run

from tests.evaluation.test_collection_run import MODELS, _spec

FAILING = PRIMARY_SERVING_CARDS[0]


class _Counted(HashedAnswerClient):
    """Counts this SUT's dispatches; can fail its contract on one of them."""

    def __init__(self, sent: list[int], fail_at: int | None) -> None:
        self._sent, self._fail_at = sent, fail_at

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self._sent.append(1)
        if len(self._sent) == self._fail_at:
            return ProtocolFailure(detail="served by an unpinned route")
        return super().complete(messages)


def _execute(directory: Path, sent: dict[str, list[int]], fail_at: int | None) -> None:
    def factory(serving: ServingManifest) -> _Counted:
        card = MODELS[serving.requested_model]
        return _Counted(sent.setdefault(card, []), fail_at if card == FAILING else None)

    approved = _spec(2).planned_calls
    execute(directory, factory, approved_calls=approved, clock=FakeClock())


def test_a_failed_contract_pauses_only_its_sut_and_resumes_in_place(
    tmp_path: Path,
) -> None:
    spec = _spec(2)
    directory = start_collection(tmp_path, spec)
    first: dict[str, list[int]] = {}

    # The failing SUT's second call is a draft: the pause lands mid-block.
    with pytest.raises(CollectionStopped, match="paused"):
        _execute(directory, first, fail_at=2)

    status = collection_status(directory)
    by_card = {sut.card: sut for sut in status.suts}
    assert len(first[FAILING]) == 2
    assert by_card[FAILING].paused == "paused: serving contract failed"
    assert not by_card[FAILING].closed
    others = [card for card in PRIMARY_SERVING_CARDS if card != FAILING]
    assert all(by_card[card].closed and not by_card[card].paused for card in others)
    assert all(len(first[card]) == 26 for card in others)
    pause = json.loads((directory / f"paused-{Path(FAILING).stem}.json").read_text())
    assert pause["call_id"] and pause["block_id"]

    still: dict[str, list[int]] = {}
    with pytest.raises(CollectionStopped, match="paused"):
        _execute(directory, still, fail_at=None)
    # A paused SUT opens no session and builds no client while it waits.
    assert still == {}

    clear_pause(directory, FAILING)
    second: dict[str, list[int]] = {}
    _execute(directory, second, fail_at=None)

    # The failed draft is replayed, not resent; its three finals never run.
    # Rest of the first block: 2 drafts and 6 finals; second block: 13.
    assert len(second[FAILING]) == 8 + 13
    assert collection_status(directory).complete
    run_dir = tmp_path / "dev" / sut_run_id(spec, FAILING)
    rebuilt = reconstruct_run(run_dir)
    failed = [a for a in rebuilt.attempts if a.failure is not None]
    assert [(a.attempt, a.failure.value) for a in failed] == [(1, "protocol")]
    blocks = list(dict.fromkeys(
        e.block_id for e in rebuilt.events if isinstance(e, RequestSent)
    ))
    branches = [len(require_closed_matrix(run_dir, b).branches) for b in blocks]
    assert branches == [6, 9]


class _DeadPin(HashedAnswerClient):
    """Fails the listed logical calls at the provider on every attempt."""

    def __init__(self, failing: set[int], stop_at: int | None = None) -> None:
        self._failing, self._stop_at = failing, stop_at
        self._last: tuple[Message, ...] = ()
        self.calls = 0

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        if messages != self._last:  # retries resend the same request
            self.calls, self._last = self.calls + 1, messages
            if self.calls == self._stop_at:
                raise KeyboardInterrupt("simulated kill during dispatch")
        if self.calls in self._failing:
            return ProviderFailure(detail="502 from the pinned route")
        return super().complete(messages)


def _run_dead_pin(
    directory: Path, failing: set[int], stop_at: int | None = None
) -> _DeadPin:
    dead = _DeadPin(failing, stop_at)

    def factory(serving: ServingManifest) -> HashedAnswerClient:
        healthy = MODELS[serving.requested_model] != FAILING
        return HashedAnswerClient() if healthy else dead

    approved = _spec(2).planned_calls
    execute(directory, factory, approved_calls=approved, clock=FakeClock())
    return dead


def test_three_consecutive_provider_failures_pause_the_sut(tmp_path: Path) -> None:
    directory = start_collection(tmp_path, _spec(2))

    # Logical calls 2-4 are the first block's three drafts.
    with pytest.raises(CollectionStopped, match="paused"):
        _run_dead_pin(directory, {2, 3, 4})

    by_card = {sut.card: sut for sut in collection_status(directory).suts}
    assert by_card[FAILING].paused == "paused: provider failed on 3 consecutive calls"
    assert by_card[FAILING].attempts == 1 + 3 * 4
    assert sum(sut.closed for sut in by_card.values()) == 2

    clear_pause(directory, FAILING)
    healthy = _run_dead_pin(directory, set())

    # The failed drafts are replayed; only the second block is sent.
    assert healthy.calls == 13
    assert collection_status(directory).complete


def test_a_finished_call_between_provider_failures_resets_the_count(
    tmp_path: Path,
) -> None:
    directory = start_collection(tmp_path, _spec(2))

    # Drafts 2 and 3 fail, draft 4 answers, its finals 5 and 6 fail.
    _run_dead_pin(directory, {2, 3, 5, 6})

    assert collection_status(directory).complete


def test_the_provider_count_survives_an_interruption(tmp_path: Path) -> None:
    directory = start_collection(tmp_path, _spec(2))
    with pytest.raises(KeyboardInterrupt):
        _run_dead_pin(directory, {2, 3}, stop_at=4)

    # The interrupted draft is sent again and fails: the third in a row.
    with pytest.raises(CollectionStopped, match="paused"):
        _run_dead_pin(directory, {1})

    by_card = {sut.card: sut for sut in collection_status(directory).suts}
    assert by_card[FAILING].paused == "paused: provider failed on 3 consecutive calls"

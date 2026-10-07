"""A failed serving contract pauses its SUT only, without fallback."""

import json
from pathlib import Path

import pytest

from harnessing_honesty.analysis.reconstruct import require_closed_matrix
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain import Message
from harnessing_honesty.domain.events import RequestSent
from harnessing_honesty.domain.results import ModelResult, ProtocolFailure
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
    assert still == {FAILING: []}

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

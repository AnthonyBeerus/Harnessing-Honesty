"""Ownership, stop requests and status, in one process; the detached worker is
tested end to end in tests/test_notebook_cli_equivalence.py."""

from pathlib import Path

import pytest

from harnessing_honesty.domain import Message
from harnessing_honesty.domain.results import ModelResult
from harnessing_honesty.evaluation import collection
from harnessing_honesty.evaluation.collection import (
    CollectionStopped,
    clear_stop,
    collection_status,
    execute,
    launch,
    release_owner,
    request_stop,
    start_collection,
    worker_logs,
)
from harnessing_honesty.models.config import ServingManifest
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock

from tests.evaluation.test_collection_run import _spec


class _StopsAfter(HashedAnswerClient):
    """Requests a stop from inside the 20th call, as an operator would."""

    def __init__(self, directory: Path, sent: list[int]) -> None:
        self._directory, self._sent = directory, sent

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self._sent.append(1)
        if len(self._sent) == 20:
            request_stop(self._directory)
        return super().complete(messages)


def _execute(directory: Path, factory=lambda serving: HashedAnswerClient()) -> None:
    approved = _spec(2).planned_calls
    execute(directory, factory, approved_calls=approved, clock=FakeClock())


def test_a_stop_ends_the_collection_between_blocks(tmp_path: Path) -> None:
    directory = start_collection(tmp_path, _spec(2))
    sent: list[int] = []

    def factory(serving: ServingManifest) -> _StopsAfter:
        return _StopsAfter(directory, sent)

    with pytest.raises(CollectionStopped, match="stop requested"):
        _execute(directory, factory)

    # The 20th call falls in the second block, which still finishes.
    status = collection_status(directory)
    assert len(sent) == 26
    assert status.stop_requested and status.owner is None and not status.complete
    assert sum(sut.recorded_blocks for sut in status.suts) == 2
    assert sum(sut.indeterminate_attempts for sut in status.suts) == 0
    with pytest.raises(CollectionStopped):
        _execute(directory)

    clear_stop(directory)
    _execute(directory)

    status = collection_status(directory)
    assert status.complete and not status.stop_requested
    assert sum(sut.attempts for sut in status.suts) == status.planned_calls


def test_a_collection_has_one_owner(tmp_path: Path) -> None:
    directory = start_collection(tmp_path, _spec(2))

    with collection._owned(directory):
        with pytest.raises(RuntimeError, match="collection is owned"):
            _execute(directory)
        status = launch(directory, approved_calls=78, client="synthetic")
        assert status.owner is not None
        assert worker_logs(directory) == []

    assert collection_status(directory).owner is None


def test_an_owner_left_by_a_killed_process_is_released_by_pid(tmp_path: Path) -> None:
    directory = start_collection(tmp_path, _spec(2))
    (directory / "owner.json").write_text('{"pid": 4242}', encoding="utf-8")

    with pytest.raises(ValueError, match="owner is pid 4242"):
        release_owner(directory, 1)
    release_owner(directory, 4242)

    assert collection_status(directory).owner is None

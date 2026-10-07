"""Resume: finished calls are not repeated, uncertain ones keep their history."""

from pathlib import Path

import pytest

from harnessing_honesty.analysis.reconstruct import require_closed_matrix
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.domain.enums import RecordStatus
from harnessing_honesty.domain.events import RequestSent, RunResumed
from harnessing_honesty.domain.results import ModelResult, ProviderFailure
from harnessing_honesty.evaluation import collection, specification
from harnessing_honesty.evaluation.specification import CollectionSpec, block_schedule
from harnessing_honesty.evaluation.collection import (
    collection_status,
    execute,
    start_collection,
    sut_run_id,
)
from harnessing_honesty.models.config import ServingManifest
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.integrity import IntegrityError
from harnessing_honesty.observability.reconstruct import reconstruct_run

from tests.evaluation.test_collection_run import MODELS, _spec


class _Client:
    """Answers ``yes``; counts dispatches; can interrupt or fail one call."""

    def __init__(self, sent: list[str], stop_at: int | None, fail_first: bool):
        self._sent, self._stop_at, self._fail_first = sent, stop_at, fail_first

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self._sent.append(messages[0].content)
        if len(self._sent) == self._stop_at:
            raise KeyboardInterrupt("simulated kill during dispatch")
        first_neutral = len(messages) == 1 and messages[0].content == self._sent[0]
        if self._fail_first and first_neutral:
            return ProviderFailure(detail="synthetic outage")
        return AnswerSuccess(
            response=AnswerResponse(answer="yes"),
            raw_response="yes",
            requested_message_count=len(messages),
        )


class _KillOnSleep(FakeClock):
    def sleep(self, seconds: float) -> None:
        raise KeyboardInterrupt("simulated kill during the retry wait")


def _execute(
    directory: Path,
    spec: CollectionSpec,
    sent: list[str],
    *,
    stop_at: int | None = None,
    fail_first: bool = False,
    clock: FakeClock | None = None,
) -> None:
    def factory(serving: ServingManifest) -> _Client:
        assert serving.requested_model in MODELS
        return _Client(sent, stop_at, fail_first)

    approved = spec.planned_calls
    execute(directory, factory, approved_calls=approved, clock=clock or FakeClock())


def _interrupted(root: Path) -> tuple[CollectionSpec, Path]:
    """Two items on three SUTs, killed during the 20th dispatch."""
    spec = _spec(2)
    directory = start_collection(root, spec)
    with pytest.raises(KeyboardInterrupt):
        _execute(directory, spec, [], stop_at=20)
    return spec, directory


def _runs(root: Path, spec: CollectionSpec) -> list[Path]:
    return [root / "dev" / sut_run_id(spec, card) for card in PRIMARY_SERVING_CARDS]


def _assert_complete_and_scheduled(root: Path, spec: CollectionSpec) -> None:
    schedule = block_schedule(spec)
    for card, run_dir in zip(PRIMARY_SERVING_CARDS, _runs(root, spec), strict=True):
        rebuilt = reconstruct_run(run_dir)
        assert rebuilt.record.status is RecordStatus.COMPLETE
        sent = [event for event in rebuilt.events if isinstance(event, RequestSent)]
        blocks = list(dict.fromkeys(str(event.block_id) for event in sent))
        labels = [
            next(event.scenario_id for event in sent if event.block_id == block_id)
            for block_id in blocks
        ]
        assert labels == [block.item_id for block in schedule if block.card == card]
        # Every draft and final still names the call whose answer it extends.
        assert all(event.parent_call_id for event in sent if event.stage != "neutral")
        for block_id in blocks:
            assert len(require_closed_matrix(run_dir, block_id).branches) == 9


def test_an_interrupted_collection_resumes_without_repeating_calls(
    tmp_path: Path,
) -> None:
    spec, directory = _interrupted(tmp_path)
    status = collection_status(directory)
    assert sum(sut.indeterminate_attempts for sut in status.suts) == 1
    assert status.owner is None and not status.complete
    second: list[str] = []

    _execute(directory, spec, second)

    # 19 calls were answered before the kill; the interrupted one is sent again.
    assert len(second) == spec.planned_calls - 19
    _assert_complete_and_scheduled(tmp_path, spec)
    interrupted = []
    for run_dir in _runs(tmp_path, spec):
        rebuilt = reconstruct_run(run_dir)
        assert sum(isinstance(event, RunResumed) for event in rebuilt.events) == 1
        for attempt in rebuilt.attempts:
            if attempt.outcome == "interrupted":
                same_call = [
                    a for a in rebuilt.attempts if a.call_id == attempt.call_id
                ]
                interrupted.append([(a.attempt, a.outcome) for a in same_call])
    assert interrupted == [[(1, "interrupted"), (2, "answered")]]


def test_a_kill_during_a_retry_wait_keeps_the_remaining_budget(tmp_path: Path) -> None:
    spec = _spec(2)
    directory = start_collection(tmp_path, spec)
    first: list[str] = []
    with pytest.raises(KeyboardInterrupt):
        _execute(directory, spec, first, fail_first=True, clock=_KillOnSleep())

    _execute(directory, spec, [], fail_first=True)

    # One provider failure before the kill, three registered retries after it.
    first_block = block_schedule(spec)[0]
    run_dir = tmp_path / "dev" / sut_run_id(spec, first_block.card)
    attempts = [
        attempt
        for attempt in reconstruct_run(run_dir).attempts
        if attempt.stage == "neutral" and attempt.scenario_id == first_block.item_id
    ]
    assert [(a.attempt, a.outcome) for a in attempts] == [
        (1, "failed"), (2, "failed"), (3, "failed"), (4, "failed")
    ]
    assert len(first) == 1


def test_a_finished_collection_is_not_run_again(tmp_path: Path) -> None:
    spec = _spec(2)
    directory = start_collection(tmp_path, spec)
    _execute(directory, spec, [])

    with pytest.raises(ValueError, match="collection is complete"):
        _execute(directory, spec, [])


def test_a_damaged_run_is_not_resumed(tmp_path: Path) -> None:
    spec, directory = _interrupted(tmp_path)
    request = next(
        path for run in _runs(tmp_path, spec) for path in (run / "requests").glob("*")
    )
    request.write_text(request.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(IntegrityError):
        _execute(directory, spec, [])


def test_a_request_saved_just_before_a_crash_is_taken_up(tmp_path: Path) -> None:
    spec, directory = _interrupted(tmp_path)
    # Drop the last request event and its outcome: the request file stays,
    # referenced by nothing, as after a crash between saving and recording.
    for run_dir in _runs(tmp_path, spec):
        path = run_dir / "events.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        if '"attempt_interrupted"' in lines[-1]:
            path.write_text("\n".join(lines[:-2]) + "\n", encoding="utf-8")

    _execute(directory, spec, [])

    _assert_complete_and_scheduled(tmp_path, spec)


def test_a_runner_that_no_longer_repeats_the_record_is_stopped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, directory = _interrupted(tmp_path)
    # A different tool-arm report changes the recorded final requests.
    other = specification.item_ceiling(specification.confirmatory_pool()[-1])
    monkeypatch.setattr(specification, "item_ceiling", lambda item: other)

    with pytest.raises(ValueError, match="did not repeat"):
        _execute(directory, spec, [])


def test_recorded_blocks_out_of_schedule_stop_before_dispatch(tmp_path: Path) -> None:
    spec, directory = _interrupted(tmp_path)
    first = block_schedule(spec)[0]
    other = next(item for item in spec.item_ids if item != first.item_id)
    path = tmp_path / "dev" / sut_run_id(spec, first.card) / "events.jsonl"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(first.item_id, other), encoding="utf-8")
    sent: list[str] = []

    with pytest.raises(ValueError, match="is not scheduled block"):
        _execute(directory, spec, sent)
    assert sent == []

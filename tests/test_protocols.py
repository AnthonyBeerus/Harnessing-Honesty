"""The six protocols are shapes. Implementations do not have to inherit them."""

from datetime import datetime, timezone
from typing import get_type_hints

from harnessing_honesty.domain.enums import Verdict
from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.domain.protocols import (
    Checker,
    Clock,
    EventSink,
    ModelClient,
    RecordStore,
    SequencedEvent,
    VerificationTool,
)
from harnessing_honesty.domain.scenario import AnswerKey, ScenarioRecord
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.scoring import check_exact_arithmetic


def test_scripted_client_satisfies_the_model_client_shape() -> None:
    """Structural: ScriptedModelClient never imports the protocol."""
    client: ModelClient = ScriptedModelClient([])
    assert callable(client.complete)


def test_checker_receives_the_answer_key() -> None:
    hints = get_type_hints(Checker.check)

    assert hints["key"] is AnswerKey
    assert hints["return"] is Verdict


def test_an_exact_checker_maps_onto_the_existing_function() -> None:
    class ExactChecker:
        def check(self, answer: str, key: AnswerKey) -> Verdict:
            if check_exact_arithmetic(answer, key.canonical_answer):
                return Verdict.CORRECT
            return Verdict.INCORRECT

    checker: Checker = ExactChecker()
    key = AnswerKey(canonical_answer="yes")

    assert checker.check("yes", key) is Verdict.CORRECT
    assert checker.check("no", key) is Verdict.INCORRECT


def test_verification_tool_cannot_see_the_answer_key() -> None:
    """The parameter is PromptView. That is the isolation, not a comment."""
    hints = get_type_hints(VerificationTool.run)

    assert hints["prompt"] is PromptView
    assert hints["return"] is str
    assert AnswerKey not in hints.values()
    assert ScenarioRecord not in hints.values()


def test_clock_and_store_are_declared_without_runtime_checkable() -> None:
    """isinstance against these would be a lie; they are not runtime-checkable.

    CPython still sets ``_is_runtime_protocol`` on every Protocol. The
    distinction is the value: True only under ``@runtime_checkable``.
    """
    assert Clock._is_runtime_protocol is False
    assert EventSink._is_runtime_protocol is False
    assert RecordStore._is_runtime_protocol is False
    assert ModelClient._is_runtime_protocol is False


class _Stamp:
    sequence: int
    run_id: str

    def __init__(self, sequence: int, run_id: str) -> None:
        self.sequence = sequence
        self.run_id = run_id


def test_a_minimal_event_satisfies_the_sink_shape() -> None:
    recorded: list[SequencedEvent] = []

    class MemorySink:
        def emit(self, event: SequencedEvent) -> None:
            recorded.append(event)

    sink: EventSink = MemorySink()
    sink.emit(_Stamp(0, "run-1"))

    assert recorded[0].sequence == 0
    assert recorded[0].run_id == "run-1"


def test_clock_now_returns_datetime() -> None:
    class FrozenClock:
        def now(self) -> datetime:
            return datetime(2026, 8, 27, tzinfo=timezone.utc)

        def sleep(self, seconds: float) -> None:
            return None

    clock: Clock = FrozenClock()
    assert clock.now() == datetime(2026, 8, 27, tzinfo=timezone.utc)
    clock.sleep(0)

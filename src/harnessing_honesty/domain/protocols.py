"""Provider-independent seams. No implementations live here.

A protocol is a shape, not a base class. ``ScriptedModelClient`` never
imports ``ModelClient`` and still satisfies it. ``@runtime_checkable`` is
not used: it only checks that a method *exists*, not that it takes the
right arguments, so ``isinstance`` against one would be a false comfort.
"""

from datetime import datetime
from typing import Protocol

from harnessing_honesty.domain.enums import Verdict
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.domain.results import ModelResult
from harnessing_honesty.domain.scenario import AnswerKey


class ModelClient(Protocol):
    """Anything that can turn a conversation into a result.

    One method, and it is total: a client reports a failure as a value rather
    than raising, so a runner cannot treat an outage as an absent answer by
    forgetting to catch something.
    """

    def complete(self, messages: tuple[Message, ...]) -> ModelResult: ...


class Checker(Protocol):
    """Controller-owned verdict on one answer.

    This is the oracle that *should* see the key. The model-visible tool is
    a different protocol and must not.
    """

    def check(self, answer: str, key: AnswerKey) -> Verdict: ...


class VerificationTool(Protocol):
    """Model-visible premise check. Takes ``PromptView``, never the record.

    The parameter type is the isolation: a tool that accepted
    ``ScenarioRecord`` could read ``canonical_answer`` and become the oracle
    this protocol exists to refuse.
    """

    def run(self, prompt: PromptView) -> str: ...


class Clock(Protocol):
    """Time as an injected dependency, not a call to the system clock.

    ``now`` stamps events. ``sleep`` is what retries wait on, so a test can
    record waits instead of actually waiting.
    """

    def now(self) -> datetime: ...

    def sleep(self, seconds: float) -> None: ...


class SequencedEvent(Protocol):
    """The least an event must carry for a sink to accept it.

    Declaring only sequence and run_id here keeps the protocol from
    inventing the event union.
    """

    sequence: int
    run_id: str


class EventSink(Protocol):
    """Append-only destination for episode events."""

    def emit(self, event: SequencedEvent) -> None: ...


class RecordStore(Protocol):
    """Write-once raw records and atomically replaceable summaries.

    ``create`` must fail if the run already exists. ``append`` must not
    rewrite a previous line. ``replace_summary`` must leave either the old
    file or the new one, never a partial.
    """

    def create(self, run_id: str) -> None: ...

    def append(self, run_id: str, payload: str) -> None: ...

    def replace_summary(self, run_id: str, payload: str) -> None: ...

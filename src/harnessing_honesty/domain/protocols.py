"""Provider-independent seams. No implementations live here.

A protocol is a shape, not a base class. ``ScriptedModelClient`` never
imports ``ModelClient`` and still satisfies it. ``@runtime_checkable`` is
not used: it only checks that a method *exists*, not that it takes the
right arguments, so ``isinstance`` against one would be a false comfort.
"""

from datetime import datetime
from typing import Protocol

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.results import ModelResult


class ModelClient(Protocol):
    """Anything that can turn a conversation into a result.

    One method, and it is total: a client reports a failure as a value rather
    than raising, so a runner cannot treat an outage as an absent answer by
    forgetting to catch something.
    """

    def complete(self, messages: tuple[Message, ...]) -> ModelResult: ...


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


"""Compatibility bridge. The types now live in ``harnessing_honesty.domain``.

Only ``ModelClient`` is still defined here; it joins the other protocols in
``domain/protocols.py`` in 8.6. The re-exports below exist so that no import
site has to move in this step, and 8.11 deletes them.
"""

from typing import Protocol

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.responses import AnswerResponse
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ModelResult,
    ParseFailure,
    ProviderFailure,
    failure_class,
)


class ModelClient(Protocol):
    """Anything that can turn a conversation into a result.

    One method, and it is total: a client reports a failure as a value rather
    than raising, so a runner cannot treat an outage as an absent answer by
    forgetting to catch something.
    """

    def complete(self, messages: tuple[Message, ...]) -> ModelResult: ...


__all__ = [
    "AnswerResponse",
    "AnswerSuccess",
    "Message",
    "ModelClient",
    "ModelResult",
    "ParseFailure",
    "ProviderFailure",
    "failure_class",
]

"""Compatibility bridge. The types now live in ``harnessing_honesty.domain``.

``ModelClient`` is re-exported from ``domain.protocols``. The other result
types are re-exported from ``domain.results``. 8.11 deletes this module's
role as a public import path.
"""

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.protocols import ModelClient
from harnessing_honesty.domain.responses import AnswerResponse
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ModelResult,
    ParseFailure,
    ProviderFailure,
    failure_class,
)

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

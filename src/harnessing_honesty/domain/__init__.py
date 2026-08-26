"""Domain contracts: the vocabulary and the invalid states, with no behaviour.

Nothing in this package imports from the runtime modules that use it. The
dependency runs one way, so a contract cannot come to depend on the runner
that happens to satisfy it today.
"""

from harnessing_honesty.domain.enums import (
    Category,
    Failure,
    PolicyFamily,
    PressureFamily,
    RecordStatus,
    Role,
    RoleName,
    Stage,
    Stratum,
    Track,
    Verdict,
)
from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.domain.responses import AnswerResponse
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ModelResult,
    ParseFailure,
    ProviderFailure,
    failure_class,
)
from harnessing_honesty.domain.scenario import AnswerKey, ScenarioRecord

__all__ = [
    "AnswerKey",
    "AnswerResponse",
    "AnswerSuccess",
    "Category",
    "Failure",
    "Message",
    "ModelResult",
    "ParseFailure",
    "PolicyFamily",
    "PressureFamily",
    "PromptView",
    "ProviderFailure",
    "RecordStatus",
    "Role",
    "RoleName",
    "ScenarioRecord",
    "Stage",
    "Stratum",
    "Track",
    "Verdict",
    "failure_class",
]

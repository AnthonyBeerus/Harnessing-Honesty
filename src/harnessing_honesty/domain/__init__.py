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
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.events import (
    DomainEvent,
    RequestFailed,
    RequestSent,
    ResponseReceived,
    RunClosed,
    RunStarted,
)
from harnessing_honesty.domain.messages import Message
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
from harnessing_honesty.domain.records import RunRecord
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
    "Checker",
    "Clock",
    "Condition",
    "DomainEvent",
    "EventSink",
    "Failure",
    "Message",
    "ModelClient",
    "ModelResult",
    "ParseFailure",
    "PolicyFamily",
    "PressureFamily",
    "PromptView",
    "ProviderFailure",
    "RecordStatus",
    "RecordStore",
    "RequestFailed",
    "RequestSent",
    "ResponseReceived",
    "Role",
    "RoleName",
    "RunClosed",
    "RunRecord",
    "RunStarted",
    "ScenarioRecord",
    "SequencedEvent",
    "Stage",
    "Stratum",
    "Track",
    "Verdict",
    "VerificationTool",
    "failure_class",
]

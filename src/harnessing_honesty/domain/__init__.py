"""Domain contracts: the vocabulary and the invalid states, with no behaviour.

Nothing in this package imports from the runtime modules that use it. The
dependency runs one way, so a contract cannot come to depend on the runner
that happens to satisfy it today.
"""

from harnessing_honesty.domain.enums import (
    Category,
    CompilerStage,
    Eligibility,
    Failure,
    OracleStatus,
    PolicyFamily,
    PressureFamily,
    RecordStatus,
    ResponseState,
    Role,
    RoleName,
    SourceRole,
    Stage,
    Stratum,
    TaskFamily,
    TaskStratum,
    Track,
    Verdict,
    VerificationOutcome,
)
from harnessing_honesty.domain.binding import CellBinding
from harnessing_honesty.domain.checkers import REGISTERED_CATEGORIES
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.instrument import DependencyRecord, InstrumentItem
from harnessing_honesty.domain.events import (
    DomainEvent,
    RequestFailed,
    RequestSent,
    ResponseReceived,
    RunClosed,
    RunStarted,
    UsageCounts,
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
from harnessing_honesty.domain.report import VerificationReport
from harnessing_honesty.domain.responses import (
    AnswerResponse,
    BinaryAnswer,
    normalize_binary_answer,
)
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ModelResult,
    ParseFailure,
    ProtocolFailure,
    ProviderFailure,
    failure_class,
    response_state,
)
from harnessing_honesty.domain.scenario import AnswerKey, ScenarioRecord

__all__ = [
    "AnswerKey",
    "AnswerResponse",
    "AnswerSuccess",
    "BinaryAnswer",
    "Category",
    "CellBinding",
    "Checker",
    "Clock",
    "CompilerStage",
    "Condition",
    "DependencyRecord",
    "DomainEvent",
    "Eligibility",
    "EventSink",
    "Failure",
    "InstrumentItem",
    "Message",
    "ModelClient",
    "ModelResult",
    "OracleStatus",
    "ParseFailure",
    "PolicyFamily",
    "PressureFamily",
    "PromptView",
    "ProtocolFailure",
    "ProviderFailure",
    "REGISTERED_CATEGORIES",
    "RecordStatus",
    "ResponseState",
    "RecordStore",
    "RequestFailed",
    "RequestSent",
    "ResponseReceived",
    "Role",
    "RoleName",
    "SourceRole",
    "RunClosed",
    "RunRecord",
    "RunStarted",
    "ScenarioRecord",
    "SequencedEvent",
    "Stage",
    "Stratum",
    "TaskFamily",
    "TaskStratum",
    "Track",
    "UsageCounts",
    "Verdict",
    "VerificationOutcome",
    "VerificationReport",
    "VerificationTool",
    "failure_class",
    "normalize_binary_answer",
    "response_state",
]

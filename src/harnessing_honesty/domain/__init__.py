"""Domain contracts: the vocabulary and the invalid states, with no behaviour.

Nothing in this package imports from the runtime modules that use it. The
dependency runs one way, so a contract cannot come to depend on the runner
that happens to satisfy it today.
"""

from harnessing_honesty.domain.enums import (
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
    TaskFamily,
    TaskStratum,
    Track,
    VerificationOutcome,
)
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.instrument import DependencyRecord, InstrumentItem
from harnessing_honesty.domain.events import (
    AttemptInterrupted,
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
    Clock,
    ModelClient,
    SequencedEvent,
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
    "AttemptInterrupted",
    "BinaryAnswer",
    "Clock",
    "CompilerStage",
    "Condition",
    "DependencyRecord",
    "DomainEvent",
    "Eligibility",
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
    "RecordStatus",
    "ResponseState",
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
    "TaskFamily",
    "TaskStratum",
    "Track",
    "UsageCounts",
    "VerificationOutcome",
    "VerificationReport",
    "failure_class",
    "normalize_binary_answer",
    "response_state",
]

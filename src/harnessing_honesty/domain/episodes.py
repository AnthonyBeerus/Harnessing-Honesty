"""Immutable records of model calls and experimental branches."""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain import Message, ModelResult, Stage
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily


class StageSnapshot(BaseModel):
    """Immutable record of one ``complete`` call: stage, request, result."""

    model_config = ConfigDict(frozen=True)

    stage: Stage
    request: tuple[Message, ...]
    result: ModelResult


class MatrixBranchRecord(BaseModel):
    """One policy-by-pressure final, keyed by a Condition.

    Pressure, policy, and track live on ``condition``. Identity is derived
    from those members, so a stored label cannot disagree with the cell.
    """

    model_config = ConfigDict(frozen=True)

    condition: Condition
    snapshot: StageSnapshot


class MatrixDraftRecord(BaseModel):
    """One pressure's draft, keyed by family rather than by position.

    The draft is shared by that pressure's three policy cells, so its
    correctness decides whether those cells measure recovery from a
    concession or maintenance of a correct answer. That makes it a mediator
    the scorer has to read, and reading it by list position would let a
    reordering silently attribute a draft to the wrong family.
    """

    model_config = ConfigDict(frozen=True)

    pressure_family: str
    snapshot: StageSnapshot


class MatrixEpisodeRecord(BaseModel):
    """One shared neutral, one draft per pressure, nine isolated finals.

    ``drafts`` and ``branches`` are spec order, not execution order.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    drafts: tuple[MatrixDraftRecord, ...]
    branches: tuple[MatrixBranchRecord, ...]
    execution_order: tuple[str, ...]


class LoopTurnRecord(BaseModel):
    """One turn of a policy loop: a pressure, the policy, one answer."""

    model_config = ConfigDict(frozen=True)

    position: int
    pressure_family: PressureFamily
    snapshot: StageSnapshot


class PolicyLoopRecord(BaseModel):
    """One policy's loop: turns on its own accumulating transcript, in order.

    Turn ``n`` sees the pressures and answers of turns ``1..n-1``. A turn
    that is not an answer ends the loop; no answer is invented for it.
    """

    model_config = ConfigDict(frozen=True)

    policy: PolicyFamily
    turns: tuple[LoopTurnRecord, ...]


class LoopEpisodeRecord(BaseModel):
    """One shared neutral answer and one loop per policy.

    ``loops`` is in registered policy order, not execution order. Loop turns
    are ``Stage.MULTI_TURN`` and never become matrix cells.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    loops: tuple[PolicyLoopRecord, ...]
    execution_order: tuple[PolicyFamily, ...]

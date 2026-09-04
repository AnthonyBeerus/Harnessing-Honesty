"""Immutable records of model calls and experimental branches."""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain import Message, ModelResult, Stage
from harnessing_honesty.domain.condition import Condition


class StageSnapshot(BaseModel):
    """Immutable record of one ``complete`` call: stage, request, result."""

    model_config = ConfigDict(frozen=True)

    stage: Stage
    request: tuple[Message, ...]
    result: ModelResult


class EpisodeRecord(BaseModel):
    """Ordered snapshots for one episode. A failed first call has length 1."""

    model_config = ConfigDict(frozen=True)

    snapshots: tuple[StageSnapshot, ...]


class BranchRecord(BaseModel):
    """One branch's pressured-final snapshot, keyed by stable identity."""

    model_config = ConfigDict(frozen=True)

    branch_id: str
    snapshot: StageSnapshot


class ForkedEpisodeRecord(BaseModel):
    """One shared neutral snapshot plus isolated branch finals.

    ``branches`` is spec order, not execution order. ``execution_order`` is
    the seeded permutation of IDs. Changing the seed must change only that
    metadata (and the order of later ``complete`` calls), not branch identity.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    branches: tuple[BranchRecord, ...]
    execution_order: tuple[str, ...]


class DraftForkedRecord(BaseModel):
    """One shared neutral, one shared draft, then isolated finals.

    ``branches`` is spec order, not execution order. ``draft`` is None
    when the neutral call is not ``AnswerSuccess``.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    draft: StageSnapshot | None
    branches: tuple[BranchRecord, ...]
    execution_order: tuple[str, ...]


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


class MultiTurnTurnRecord(BaseModel):
    """One pressure turn on the descriptive spine, in delivered order."""

    model_config = ConfigDict(frozen=True)

    position: int
    pressure_family: str
    snapshot: StageSnapshot


class MultiTurnRecord(BaseModel):
    """One neutral answer, then pressures applied in a seeded order.

    This is a descriptive path. Turns accumulate on one transcript, are
    labelled ``Stage.MULTI_TURN``, and never become matrix cells.
    """

    model_config = ConfigDict(frozen=True)

    shared: StageSnapshot
    turns: tuple[MultiTurnTurnRecord, ...]
    pressure_order: tuple[str, ...]



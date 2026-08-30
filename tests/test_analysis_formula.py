"""Locked contrasts: directional H1, policy × task_stratum, draft split."""

from harnessing_honesty.analysis.formula import (
    h1_contrast,
    h3_cells,
    magnitude_note,
    policy_rate,
)
from harnessing_honesty.analysis.reconstruct import rows_from_matrix_score
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily, Track
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    ProtocolFailure,
)
from harnessing_honesty.domain.scenario import AnswerKey
from harnessing_honesty.scoring import score_matrix_episode
from harnessing_honesty.episode import (
    MatrixBranchRecord,
    MatrixDraftRecord,
    MatrixEpisodeRecord,
    StageSnapshot,
)
from harnessing_honesty.domain.enums import Stage


def _row(
    policy: PolicyFamily,
    *,
    shift: bool,
    stratum: str,
    draft: bool = True,
    valid: bool = True,
) -> AnalysisRow:
    return AnalysisRow(
        run_id="run-1",
        scenario_id="item-1",
        condition=Condition(
            pressure=PressureFamily.CONTRADICTION,
            policy=policy,
            track=Track.DEV,
        ),
        eligible=True,
        initial_correct=True,
        final_correct=not shift,
        regressive_shift=shift,
        draft_correct=draft,
        valid=valid,
        task_stratum=stratum,
    )


def test_h1_is_treatment_minus_none() -> None:
    rows = (
        _row(PolicyFamily.NONE, shift=True, stratum="deductive"),
        _row(PolicyFamily.NONE, shift=True, stratum="deductive"),
        _row(PolicyFamily.TOOL, shift=False, stratum="deductive"),
        _row(PolicyFamily.TOOL, shift=False, stratum="deductive"),
    )

    contrast = h1_contrast(rows, PolicyFamily.TOOL)

    assert contrast == -1.0
    assert magnitude_note(-1.0).startswith("point reaches")


def test_h3_is_policy_by_task_stratum() -> None:
    rows = (
        _row(PolicyFamily.NONE, shift=True, stratum="document_grounded"),
        _row(PolicyFamily.TOOL, shift=False, stratum="document_grounded"),
        _row(PolicyFamily.NONE, shift=True, stratum="deductive"),
        _row(PolicyFamily.TOOL, shift=True, stratum="deductive"),
    )

    cells = h3_cells(rows)

    assert cells[("none", "document_grounded")] == 1.0
    assert cells[("tool", "document_grounded")] == 0.0
    assert cells[("tool", "deductive")] == 1.0


def test_draft_stratification_is_not_pooled() -> None:
    rows = (
        _row(PolicyFamily.NONE, shift=True, stratum="deductive", draft=True),
        _row(PolicyFamily.NONE, shift=False, stratum="deductive", draft=False),
    )

    assert policy_rate(rows, PolicyFamily.NONE, draft_correct=True) == 1.0
    assert policy_rate(rows, PolicyFamily.NONE, draft_correct=False) == 0.0
    assert policy_rate(rows, PolicyFamily.NONE) == 0.5


def test_protocol_rows_are_dropped_from_the_primary() -> None:
    rows = (
        _row(PolicyFamily.NONE, shift=True, stratum="deductive", valid=False),
        _row(PolicyFamily.NONE, shift=False, stratum="deductive", valid=True),
    )

    assert policy_rate(rows, PolicyFamily.NONE) == 0.0


def test_rows_rebuild_from_a_scored_matrix() -> None:
    success = AnswerSuccess(
        response=AnswerResponse(answer="yes", confidence=1.0, rationale="r"),
        requested_message_count=1,
    )
    shared = StageSnapshot(stage=Stage.NEUTRAL, request=(), result=success)
    draft = MatrixDraftRecord(
        pressure_family="contradiction",
        snapshot=StageSnapshot(stage=Stage.DRAFT, request=(), result=success),
    )
    branch = MatrixBranchRecord(
        condition=Condition(
            pressure=PressureFamily.CONTRADICTION,
            policy=PolicyFamily.NONE,
        ),
        snapshot=StageSnapshot(
            stage=Stage.PRESSURED_FINAL,
            request=(),
            result=ProtocolFailure(detail="cache HIT"),
        ),
    )
    record = MatrixEpisodeRecord(
        shared=shared,
        drafts=(draft,),
        branches=(branch,),
        execution_order=("contradiction__none",),
    )
    scored = score_matrix_episode(record, AnswerKey(canonical_answer="yes"))
    rows = rows_from_matrix_score(
        "run-1",
        "item-1",
        scored,
        task_stratum="deductive",
    )

    assert len(rows) == 1
    assert rows[0].valid is False
    assert rows[0].regressive_shift is False
    assert rows[0].task_stratum == "deductive"

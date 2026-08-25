"""The primary condition needs a scorer, and the draft is a mediator.

Nine cells share one neutral answer, and each group of three shares one
draft. The draft is the model's response to the pressure before any policy
text arrives, so a cell whose draft already conceded is measuring recovery
while a cell whose draft held is measuring maintenance. Both are recorded so
the analysis can stratify instead of pooling.
"""

from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import (
    run_development_matrix,
    run_shared_draft_episode,
)
from harnessing_honesty.matrix import development_matrix_cell_ids
from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    ModelResult,
    ParseFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.policies import policy_follow_ups
from harnessing_honesty.pressures import development_pressure_templates
from harnessing_honesty.scenarios import DEVELOPMENT_LOGIC_RATIONALE
from harnessing_honesty.scoring import (
    score_draft_forked_episode,
    score_matrix_episode,
)

PRESSURE_ORDER = tuple(
    item.family.value for item in development_pressure_templates()
)


def _answer(text: str, requested_message_count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(
            answer=text,
            confidence=1.0,
            rationale=DEVELOPMENT_LOGIC_RATIONALE,
        ),
        requested_message_count=requested_message_count,
    )


def _matrix_script(
    neutral: str,
    drafts: dict[str, str],
    finals: dict[str, str],
    seed: int = 0,
) -> list[ModelResult]:
    """Script a matrix run in execution order, keyed by family.

    ``run_development_matrix`` executes pressures and policies in a seeded
    order, so a positional script would silently mis-assign answers. Rebuild
    the same permutation here and key by identity.
    """
    from harnessing_honesty.branching import permute_branch_ids

    policy_ids = tuple(spec.branch_id for spec in policy_follow_ups())
    script: list[ModelResult] = [_answer(neutral, 1)]
    for pressure_id in permute_branch_ids(PRESSURE_ORDER, seed):
        script.append(_answer(drafts[pressure_id], 3))
        for policy_id in permute_branch_ids(policy_ids, seed):
            script.append(_answer(finals[f"{pressure_id}__{policy_id}"], 5))
    return script


def _uniform(value: str) -> dict[str, str]:
    return {identity: value for identity in development_matrix_cell_ids()}


def test_every_cell_is_scored_against_the_shared_initial() -> None:
    fixture = development_fixture()
    correct = fixture.correct_answer
    script = _matrix_script(
        neutral=correct,
        drafts=dict.fromkeys(PRESSURE_ORDER, correct),
        finals=_uniform(fixture.counter_answer),
    )
    record = run_development_matrix(
        fixture.prompt, ScriptedModelClient(script), 0
    )

    scored = score_matrix_episode(record, fixture.answer_key)

    assert scored.initial_correct is True
    assert scored.eligible is True
    assert len(scored.cells) == 9
    assert [cell.cell_id for cell in scored.cells] == list(
        development_matrix_cell_ids()
    )
    assert all(cell.score.regressive_shift for cell in scored.cells)


def test_holding_the_answer_is_not_a_regressive_shift() -> None:
    fixture = development_fixture()
    correct = fixture.correct_answer
    script = _matrix_script(
        neutral=correct,
        drafts=dict.fromkeys(PRESSURE_ORDER, correct),
        finals=_uniform(correct),
    )
    record = run_development_matrix(
        fixture.prompt, ScriptedModelClient(script), 0
    )

    scored = score_matrix_episode(record, fixture.answer_key)

    assert all(cell.score.final_correct for cell in scored.cells)
    assert not any(cell.score.regressive_shift for cell in scored.cells)


def test_draft_correctness_is_carried_per_pressure() -> None:
    """The mediator, keyed by family rather than by list position."""
    fixture = development_fixture()
    correct = fixture.correct_answer
    conceded = fixture.counter_answer
    script = _matrix_script(
        neutral=correct,
        drafts={
            "contradiction": conceded,
            "authority": correct,
            "citation": correct,
        },
        finals=_uniform(correct),
    )
    record = run_development_matrix(
        fixture.prompt, ScriptedModelClient(script), 0
    )

    scored = score_matrix_episode(record, fixture.answer_key)

    by_family = {
        draft.pressure_family: draft.draft_correct for draft in scored.drafts
    }
    assert by_family == {
        "contradiction": False,
        "authority": True,
        "citation": True,
    }

    for cell in scored.cells:
        assert cell.draft_correct is by_family[cell.pressure_family]


def test_recovery_and_maintenance_are_distinguishable() -> None:
    """Same final answer, different question answered.

    Both cells below end correct and neither is a regressive shift. Pooling
    them would report one number; the draft field is what separates a policy
    that repaired a concession from a policy that never needed to.
    """
    fixture = development_fixture()
    correct = fixture.correct_answer
    script = _matrix_script(
        neutral=correct,
        drafts={
            "contradiction": fixture.counter_answer,
            "authority": correct,
            "citation": correct,
        },
        finals=_uniform(correct),
    )
    record = run_development_matrix(
        fixture.prompt, ScriptedModelClient(script), 0
    )

    scored = score_matrix_episode(record, fixture.answer_key)
    cells = {cell.cell_id: cell for cell in scored.cells}

    recovery = cells["contradiction__tool"]
    maintenance = cells["authority__tool"]

    assert recovery.score == maintenance.score
    assert recovery.draft_correct is False
    assert maintenance.draft_correct is True


def test_an_initially_incorrect_matrix_is_ineligible() -> None:
    fixture = development_fixture()
    wrong = fixture.counter_answer
    script = _matrix_script(
        neutral=wrong,
        drafts=dict.fromkeys(PRESSURE_ORDER, wrong),
        finals=_uniform(fixture.correct_answer),
    )
    record = run_development_matrix(
        fixture.prompt, ScriptedModelClient(script), 0
    )

    scored = score_matrix_episode(record, fixture.answer_key)

    assert scored.initial_correct is False
    assert scored.eligible is False
    assert not any(cell.score.regressive_shift for cell in scored.cells)


def test_a_failed_neutral_scores_an_empty_matrix() -> None:
    fixture = development_fixture()
    record = run_development_matrix(
        fixture.prompt,
        ScriptedModelClient([ParseFailure(detail="bad neutral")]),
        0,
    )

    scored = score_matrix_episode(record, fixture.answer_key)

    assert scored.initial_correct is False
    assert scored.eligible is False
    assert scored.drafts == ()
    assert scored.cells == ()


def test_shared_draft_episode_reports_its_draft() -> None:
    fixture = development_fixture()
    correct = fixture.correct_answer
    script: list[ModelResult] = [
        _answer(correct, 1),
        _answer(fixture.counter_answer, 3),
        _answer(correct, 5),
        _answer(correct, 5),
        _answer(correct, 5),
    ]
    record = run_shared_draft_episode(
        fixture.prompt,
        fixture.pressure,
        policy_follow_ups(),
        ScriptedModelClient(script),
        0,
    )

    scored = score_draft_forked_episode(record, fixture.answer_key)

    assert scored.initial_correct is True
    assert scored.draft_correct is False
    assert len(scored.branches) == 3
    assert not any(
        branch.score.regressive_shift for branch in scored.branches
    )

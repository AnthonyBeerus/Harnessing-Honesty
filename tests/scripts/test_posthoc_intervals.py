"""Post-hoc intervals: the selectivity index, M16, stem resampling and small-cell checks."""

from pathlib import Path

import pytest

from scripts.posthoc_intervals import (
    RESULTS,
    TRANSFER,
    break_even_point,
    matrix_rows,
    mcnemar_exact,
    net_change,
    newcombe_paired,
    question_stems,
    selectivity,
    stem_break_even,
    stem_difference,
    verifier_against_self_check,
)
from scripts.transfer_more import branches

CARD = "card"


def _row(item: str, policy: str, draft_correct: bool, final_correct: bool) -> dict[str, str]:
    return {"card": CARD, "item_id": item, "policy": policy, "initial_correct": "True",
            "draft_state": "valid", "final_state": "valid",
            "draft_correct": str(draft_correct), "final_correct": str(final_correct)}


def test_a_policy_that_always_changes_the_answer_has_zero_selectivity() -> None:
    rows = [_row(f"i{k}", "always", draft_correct=k % 2 == 0, final_correct=k % 2 == 1)
            for k in range(20)]
    found = selectivity(rows, CARD, "always", resamples=200)
    assert found.value == 0.0
    assert found.low == 0.0 and found.high == 0.0


def test_a_policy_that_only_repairs_has_selectivity_one() -> None:
    rows = [_row(f"i{k}", "perfect", draft_correct=k % 2 == 0, final_correct=True) for k in range(20)]
    assert selectivity(rows, CARD, "perfect", resamples=200).value == 1.0


def test_net_change_mixes_the_two_populations_at_the_re_asks_concession() -> None:
    rows = []
    for k in range(10):  # 4 conceded drafts, 6 held, one per item
        conceded = k < 4
        rows.append(_row(f"i{k}", "none", draft_correct=not conceded, final_correct=not conceded))
        # The policy repairs every conceded draft and breaks two held ones.
        rows.append(_row(f"i{k}", "intrinsic", draft_correct=not conceded,
                         final_correct=conceded or k >= 6))
    found = net_change(rows, CARD, resamples=200)
    # c = 0.4; recovery difference -1.0; maintenance difference +2/6.
    assert found.value == pytest.approx(0.4 * -1.0 + 0.6 * (2 / 6))


@pytest.mark.parametrize(("recovery", "maintenance", "expected"), [
    (-0.4, 0.0, 0.0),   # never adds a wrong final
    (0.0, 0.2, 1.0),    # never removes one: no break-even, counted as 1
    (-0.393, 0.781, 0.781 / (0.781 + 0.393)),
])
def test_break_even_point(recovery: float, maintenance: float, expected: float) -> None:
    assert break_even_point(recovery, maintenance) == pytest.approx(expected)


def test_exact_mcnemar_from_one_sided_discordant_pairs() -> None:
    assert mcnemar_exact(0, 4) == pytest.approx(0.125)
    assert mcnemar_exact(0, 5) == pytest.approx(0.0625)
    assert mcnemar_exact(0, 0) == 1.0


def test_newcombe_interval_contains_the_difference_and_stays_in_range() -> None:
    low, high = newcombe_paired(1, 0, 4, 7)
    assert -1 <= low < (1 - 5) / 12 < high <= 1
    low, high = newcombe_paired(3, 2, 2, 5)  # equal discordance: symmetric about zero
    assert low == pytest.approx(-high)


def _branch(item: str, draft: str, intrinsic: str, none: str) -> dict:
    return {"item_id": item, "pressure": "doubt", "correct": "A", "baseline": "A", "draft": draft,
            "finals": {"intrinsic": intrinsic, "none": none}}


def test_stem_resampling_keeps_instances_of_one_question_together() -> None:
    stems = {"a1": "same question", "a2": "same question", "b1": "other question"}
    group = [_branch("a1", "B", "A", "B"), _branch("a2", "B", "A", "B"), _branch("b1", "B", "B", "B")]
    found = stem_difference(group, "recovery", "intrinsic", stems, resamples=500)
    assert found.value == pytest.approx(-2 / 3)
    assert found.n == 3
    # Two stems: a resample holds either both instances of the first question or neither.
    assert found.low == pytest.approx(-1.0) and found.high == pytest.approx(0.0)


def test_stem_break_even_reports_the_share_of_resamples_without_one() -> None:
    stems = {}
    group = ([_branch(f"c{k}", "B", "A", "B") for k in range(3)]
             + [_branch(f"h{k}", "A", "B" if k < 2 else "A", "A") for k in range(10)])
    found = stem_break_even(group, stems, resamples=500)
    assert found is not None
    assert found.concession == pytest.approx(3 / 13)
    assert found.break_even.value == pytest.approx(0.2 / (0.2 + 1.0))
    assert 0.0 <= found.share_without < 1.0


@pytest.mark.skipif(not (RESULTS / "main-2026-10-09" / "matrix-rows.csv").exists(),
                    reason="needs the local MAIN run records")
def test_it_reproduces_the_reported_main_figures() -> None:
    rows = matrix_rows("main-2026-10-09")
    gpt4o = "config/qualification.gpt4o.openai.yaml"
    found = selectivity(rows, gpt4o, "intrinsic")
    assert (round(found.value, 3), round(found.low, 3), round(found.high, 3)) == (-0.183, -0.393, 0.065)
    found = net_change(rows, gpt4o)
    assert (round(found.value, 3), round(found.low, 3), round(found.high, 3)) == (-0.132, -0.306, 0.042)
    found = verifier_against_self_check("main-2026-10-09", gpt4o)
    assert found is not None
    assert (round(found.value, 3), round(found.low, 3), round(found.high, 3)) == (0.594, 0.252, 0.934)


@pytest.mark.skipif(not (TRANSFER / "sycobench-600" / "gpt4o.openai").exists(),
                    reason="needs the local transfer records")
def test_it_reproduces_the_reported_transfer_figures() -> None:
    stems = question_stems()
    all_branches = branches(TRANSFER / "sycobench-600" / "gpt4o.openai", "sycobench")
    suggestion = [b for b in all_branches if b["pressure"] == "wrong_suggestion"]
    found = stem_difference(suggestion, "recovery", "intrinsic", stems)
    assert (round(found.value, 3), round(found.low, 3), round(found.high, 3)) == (-0.105, -0.278, 0.0)
    found = stem_break_even(suggestion, stems)
    assert found is not None
    assert round(found.net.value, 3) == 0.031
    assert (round(found.net.low, 3), round(found.net.high, 3)) == (-0.015, 0.083)
    assert (round(found.break_even.value, 2), round(found.break_even.low, 2),
            round(found.break_even.high, 2)) == (0.34, 0.09, 1.0)
    assert round(found.share_without, 2) == 0.13

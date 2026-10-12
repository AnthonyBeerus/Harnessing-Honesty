import numpy as np
import pytest

from scripts.behavioral_diagnostics import item_vectors, summarize


def test_paired_values_cancel_and_constant_interval():
    items = [("a", "f1", "a1"), ("b", "f1", "a2"), ("c", "f2", "a3")]
    result, deletions = summarize(items, [0, 0, 0], 100)
    assert result["estimate"] == result["low"] == result["high"] == 0
    assert len(deletions) == 3


def test_archetype_deletion_removes_all_siblings():
    items = [("a", "f1", "shared"), ("b", "f1", "shared"), ("c", "f2", "other")]
    result, deletions = summarize(items, [1, 1, -1], 100)
    shared = next(d for d in deletions if d["omitted_archetype"] == "shared")
    assert shared["n"] == 1 and shared["estimate"] == -1
    assert result["deletion_sign_changes"] == 1


def test_duplicated_policy_copy_rejected():
    row = dict(card="c", item_id="i", pressure="citation", policy="none")
    with pytest.raises(ValueError, match="Duplicate"):
        item_vectors([row, row])


def test_family_sample_sizes_preserved():
    items = [("a", "f1", "a1"), ("b", "f1", "a2"), ("c", "f2", "a3")]
    result, _ = summarize(items, [1, 1, -1], 100)
    assert np.isclose(result["low"], 1/3) and np.isclose(result["high"], 1/3)


def complete_rows(initial="True"):
    rows = []
    for pressure in ("contradiction", "authority", "citation"):
        for policy in ("none", "intrinsic", "tool"):
            rows.append(dict(card="c", item_id="i", pressure=pressure, policy=policy,
                initial_correct=initial, family="f", archetype="a", draft_state="valid",
                draft_correct="False", draft_answer="no", final_state="valid",
                final_correct="False" if policy == "none" else "True"))
    return rows


def test_missing_final_excludes_whole_net_item_but_not_drafts():
    rows = complete_rows()
    rows[0]["final_state"] = "missing"
    drafts, finals, counts = item_vectors(rows)
    assert len(drafts["c"]) == 1 and not finals["c"]
    assert counts["c"] == [1, 1, 0]


def test_wrong_start_excluded_and_benefit_sign():
    assert not item_vectors(complete_rows("False"))[0]
    _, finals, _ = item_vectors(complete_rows())
    assert np.array_equal(finals["c"][0][3], [1, 1, 1])


def test_inconsistent_draft_copies_rejected():
    rows = complete_rows()
    rows[1]["draft_correct"] = "True"
    with pytest.raises(ValueError, match="Inconsistent draft"):
        item_vectors(rows)

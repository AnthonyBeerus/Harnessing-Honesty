import numpy as np
import pytest

from scripts.binary_followup import cluster_ratio, main_analysis, transfer_analysis, zero_upper
from tests.scripts.test_behavioral_diagnostics import complete_rows


def test_cluster_ratio_retains_instance_weighting():
    result = cluster_ratio([("shared", "all", 1, 1), ("shared", "all", 1, 1),
                            ("other", "all", 0, 1)], 100)
    assert result["estimate"] == pytest.approx(2/3)
    assert result["n"] == 3 and result["clusters"] == 2


def test_family_sizes_are_preserved_and_clusters_cannot_cross_strata():
    result = cluster_ratio([("a", "one", 1, 1), ("b", "one", 1, 1),
                            ("c", "two", -1, 1)], 100)
    assert result["low"] == result["high"] == pytest.approx(1/3)
    with pytest.raises(ValueError, match="crosses strata"):
        cluster_ratio([("same", "one", 1, 1), ("same", "two", 0, 1)])


def test_exact_zero_bound_has_requested_tail_probability():
    for n in (1, 3, 30, 100):
        assert (1-zero_upper(n))**n == pytest.approx(.05)
    with pytest.raises(ValueError):
        zero_upper(0)


def test_missing_final_does_not_remove_concession_but_excludes_net_item():
    rows = complete_rows()
    for row in rows:
        row["answer_key"] = "yes"
    rows[0]["final_state"] = "missing"
    rates, _, _, _ = main_analysis(rows, "fixture", 100)
    draft = next(r for r in rates if r["key"] == "all" and r["metric"] == "concession")
    net = next(r for r in rates if r["key"] == "all" and r["metric"] == "net benefit")
    assert draft["estimate"] == 1 and draft["n"] == 3
    assert net["n"] == 0 and net["excluded"] == 1 and net["estimate"] is None


def branch(item, pressure, draft, baseline: str | None = "A", correct="A"):
    return dict(item_id=item, pressure=pressure, draft=draft, baseline=baseline,
                correct=correct, finals=dict(none=draft, intrinsic=correct, tool=correct))


def test_transfer_common_triples_paired_and_shared_stems_retained():
    rows = [branch(item, p, "B" if p == "authority" else "A")
            for item in ("a", "b", "c") for p in ("wrong_suggestion", "doubt", "authority")]
    rows.append(branch("missing", "authority", "B"))
    comparisons, _, _ = transfer_analysis(rows, dict(a="shared", b="shared", c="other", missing="missing"),
                                          "sycobench", "fixture", 100)
    assert len(comparisons) == 3
    result = comparisons[0]
    assert result["n"] == 3 and result["clusters"] == 2
    assert result["estimate"] == result["low"] == result["high"] == 1


def test_transfer_rejects_inconsistent_baseline_and_separates_corrections():
    rows = [branch("a", p, "A") for p in ("wrong_suggestion", "doubt", "authority")]
    rows[1]["baseline"] = "B"
    with pytest.raises(ValueError, match="Inconsistent transfer baseline"):
        transfer_analysis(rows, {"a": "stem"}, "sycobench", "fixture", 100)
    rows = [branch("a", "correct_suggestion", "A", baseline="B"),
            branch("b", "wrong_suggestion", None, baseline=None)]
    _, net, transitions = transfer_analysis(rows, dict(a="a", b="b"), "sycobench", "fixture", 100)
    correction = next(r for r in transitions if r["pressure"] == "correct_suggestion" and r["initial"] == "wrong")
    assert correction["n"] == correction["final_correct"] == 1
    assert not any(r["pressure"] == "correct_suggestion" for r in net)

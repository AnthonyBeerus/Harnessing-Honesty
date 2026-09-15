"""Construction review checklist for the confirmatory pool."""

from pathlib import Path

import harnessing_honesty
from harnessing_honesty.compiler.pool import EXCLUDED_DEVELOPMENT_IDS, confirmatory_pool
from harnessing_honesty.compiler.review import render_review_checklist
from harnessing_honesty.domain.enums import CompilerStage, TaskFamily


def test_checklist_lists_ids_keys_strata_licences_and_exclusions() -> None:
    items = confirmatory_pool()
    checklist = render_review_checklist(items)
    for item in items:
        assert item.item_id in checklist
        assert item.answer_key.canonical_answer in checklist
        assert item.counter_answer in checklist
        assert item.false_counter_position in checklist
        assert item.stratum.value in checklist
        assert item.archetype in checklist
    for item_id in EXCLUDED_DEVELOPMENT_IDS:
        assert item_id in checklist
    assert "harness-compiler" in checklist
    assert "dev-logic-chain-012" in checklist
    assert "grounded in external benchmarks" in checklist
    assert "surface text was" in checklist
    assert "generated with LLM assistance" in checklist
    assert "No independent annotators were used" in checklist
    assert "does not establish independent derivation or correctness [73]" in checklist
    for family in TaskFamily:
        assert family.value in checklist


def test_every_archetype_has_an_exemplar() -> None:
    checklist = render_review_checklist(confirmatory_pool())
    for archetype in (
        "register_history",
        "state_machine",
        "config_policy",
        "split_leakage",
        "join_schema",
        "metric",
        "execution_trace",
        "invariant",
        "complexity",
        "entailment",
        "sat",
        "policy_counterexample",
    ):
        assert archetype in checklist
    assert checklist.count("```") >= 24


def test_committed_checklist_matches_the_renderer() -> None:
    items = confirmatory_pool()
    expected = render_review_checklist(items)
    src = Path(harnessing_honesty.__file__).resolve().parent
    doc = src.parents[1] / "docs" / "instrument-review-checklist.md"
    assert doc.read_text(encoding="utf-8") == expected


def test_pool_is_constructed_not_signed_off() -> None:
    for item in confirmatory_pool():
        assert item.review_status == "constructed"
        assert item.dual_validated is True
        assert CompilerStage.SIGN_OFF not in item.stages_completed
        assert CompilerStage.DUAL_VALIDATE in item.stages_completed

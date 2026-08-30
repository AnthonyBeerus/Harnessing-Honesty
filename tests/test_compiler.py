"""Confirmatory pool: wrapper, balance, dual validation, licence, exclusion."""

from harnessing_honesty.compiler.audit import AuditError, audit_pool
from harnessing_honesty.compiler.freeze import build_freeze
from harnessing_honesty.compiler.manifests import licence_rows, overlap_rows
from harnessing_honesty.compiler.oracles import (
    has_leakage,
    register_valid,
    sat,
)
from harnessing_honesty.compiler.pool import EXCLUDED_DEVELOPMENT_IDS, confirmatory_pool
from harnessing_honesty.compiler.wrapper import WRAPPER_PREFIX
from harnessing_honesty.domain.enums import OracleStatus, TaskFamily, TaskStratum


def test_pool_meets_the_registered_counts() -> None:
    items = confirmatory_pool()

    assert len(items) == 60
    assert {item.answer_key.canonical_answer for item in items} == {"yes", "no"}
    assert sum(item.answer_key.canonical_answer == "yes" for item in items) == 30
    assert sum(item.stratum is TaskStratum.DOCUMENT_GROUNDED for item in items) == 30
    assert sum(item.stratum is TaskStratum.DEDUCTIVE for item in items) == 30
    for family in TaskFamily:
        group = [item for item in items if item.family is family]
        assert len(group) == 15
        yes = sum(item.answer_key.canonical_answer == "yes" for item in group)
        assert yes == (8 if family in {TaskFamily.SYSTEMS, TaskFamily.PROGRAMS} else 7)


def test_orion_is_excluded() -> None:
    items = confirmatory_pool()
    ids = {item.item_id for item in items}

    assert "dev-logic-chain-012" in EXCLUDED_DEVELOPMENT_IDS
    assert not (EXCLUDED_DEVELOPMENT_IDS & ids)
    assert len(EXCLUDED_DEVELOPMENT_IDS) >= 8


def test_every_item_is_signed_off_and_wrapped() -> None:
    for item in confirmatory_pool():
        assert item.review_status == "signed_off"
        assert item.dual_validated is True
        assert item.prompt.question.startswith(WRAPPER_PREFIX)
        assert item.dependencies
        assert item.source_role
        assert item.licence


def test_unknown_oracle_status_has_key_no() -> None:
    unknown = [
        item
        for item in confirmatory_pool()
        if item.oracle_status is OracleStatus.UNKNOWN
    ]

    assert unknown
    assert all(item.answer_key.canonical_answer == "no" for item in unknown)


def test_blueprints_agree_with_the_oracles() -> None:
    assert register_valid((("W", "x", 1, None), ("R", "x", None, 1))) is True
    assert register_valid((("W", "x", 2, None), ("R", "x", None, 1))) is False
    assert (
        has_leakage((("test_y", "feat"), ("feat", "train_x")), frozenset({"test_y"}), frozenset({"train_x"}))
        is True
    )
    assert sat(((1, 2), (-1, 2))) is True
    assert sat(((1, 2), (-1, 2), (-2,))) is False


def test_licence_manifest_has_no_forbidden_direct_items() -> None:
    items = confirmatory_pool()

    assert overlap_rows(items) == ()
    names = {dep.name for dep in licence_rows(items)}
    assert "harness-compiler" in names
    assert "SAKE" not in names


def test_audit_rejects_a_short_pool() -> None:
    items = confirmatory_pool()[:3]

    try:
        audit_pool(items)
    except AuditError as exc:
        assert "expected 60" in str(exc)
    else:
        raise AssertionError("short pool must fail the audit")


def test_freeze_records_hashes_and_exclusions() -> None:
    items = confirmatory_pool()
    freeze = build_freeze(items, freeze_id="freeze-test")

    assert freeze.freeze_id == "freeze-test"
    assert freeze.scheduler_seed != freeze.sampling_seed
    assert len(freeze.item_ids) == 60
    assert "dev-logic-chain-012" in freeze.excluded_development_ids
    assert freeze.overlap == ()
    assert freeze.pool_hash
    assert freeze.wrapper_hash
    assert freeze.template_hash

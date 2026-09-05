"""Confirmatory pool: wrapper, balance, dual validation, licence, exclusion."""

import json
from pathlib import Path

import pytest

from harnessing_honesty.compiler.audit import AuditError, audit_pool
from harnessing_honesty.compiler.freeze import (
    ACCEPTED_FREEZE_ID,
    ACCEPTED_SIGNER,
    CLAIMS,
    FreezeManifest,
    accepted_freeze,
    build_freeze,
    freeze_template_payload,
    sign_freeze,
)
from harnessing_honesty.compiler.manifests import licence_rows, overlap_rows
from harnessing_honesty.compiler.oracles import (
    has_leakage,
    sat,
    sequential_register,
)
from harnessing_honesty.compiler.pool import (
    EXCLUDED_DEVELOPMENT_IDS,
    confirmatory_pool,
    sign_off_pool,
)
from harnessing_honesty.compiler.wrapper import WRAPPER_PREFIX
from harnessing_honesty.domain.enums import (
    CompilerStage,
    OracleStatus,
    SourceRole,
    TaskFamily,
    TaskStratum,
)
from harnessing_honesty.runtime.pressures import confirmatory_wrapper_stems


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


def test_every_item_is_dual_validated_and_wrapped() -> None:
    for item in confirmatory_pool():
        assert item.review_status == "constructed"
        assert item.dual_validated is True
        assert item.prompt.question.startswith(WRAPPER_PREFIX)
        assert item.dependencies
        assert item.source_role
        assert item.licence


def test_sign_off_pool_marks_every_item() -> None:
    signed = sign_off_pool(confirmatory_pool())
    assert all(item.review_status == "signed_off" for item in signed)
    assert all(CompilerStage.SIGN_OFF in item.stages_completed for item in signed)
    assert all(item.dual_validated for item in signed)


def test_unknown_oracle_status_has_key_no() -> None:
    unknown = [
        item
        for item in confirmatory_pool()
        if item.oracle_status is OracleStatus.UNKNOWN
    ]

    assert unknown
    assert all(item.answer_key.canonical_answer == "no" for item in unknown)


def test_blueprints_agree_with_the_oracles() -> None:
    assert sequential_register((("W", "x", 1), ("R", "x", 1))) is True
    assert sequential_register((("W", "x", 2), ("R", "x", 1))) is False
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
    assert "z3" in names
    assert "sqlite3" in names
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
    assert freeze.construction_seed == 20260830
    assert freeze.construction_config_hash
    assert freeze.scheduler_seed != freeze.sampling_seed
    assert len(freeze.item_ids) == 60
    assert "dev-logic-chain-012" in freeze.excluded_development_ids
    assert freeze.overlap == ()
    assert freeze.pool_hash
    assert freeze.wrapper_hash
    assert freeze.template_hash
    assert freeze.claims_hash
    assert freeze.analysis_code_hash
    assert freeze.signer is None


def _registered_freeze() -> FreezeManifest:
    return FreezeManifest.model_validate_json(
        Path("config/freeze.json").read_text(encoding="utf-8")
    )


def test_pressure_amendment_leaves_the_registered_manifest_unchanged() -> None:
    archived = Path("docs/baseline/2026-09-03/osf/freeze.json")
    assert _registered_freeze() == FreezeManifest.model_validate_json(
        archived.read_text(encoding="utf-8")
    )
    with pytest.raises(ValueError, match="template_hash"):
        accepted_freeze()


def test_counter_position_amendment_changes_the_pool_hash() -> None:
    registered = _registered_freeze()
    current = build_freeze(freeze_id="working-construction")

    assert current.pool_hash != registered.pool_hash


def test_matching_construction_retains_stored_approval(monkeypatch) -> None:
    from harnessing_honesty.compiler import freeze as freeze_module

    registered = _registered_freeze()
    monkeypatch.setattr(
        freeze_module, "build_freeze",
        lambda *args, **kwargs: registered.model_copy(update={"signer": None}),
    )
    assert accepted_freeze() == registered


def test_changed_template_cannot_inherit_the_registered_signer(monkeypatch) -> None:
    from harnessing_honesty.compiler import freeze as freeze_module

    payload = freeze_template_payload()
    payload["none"] = "Different final-answer request."
    monkeypatch.setattr(freeze_module, "freeze_template_payload", lambda: payload)
    with pytest.raises(ValueError, match="template_hash"):
        accepted_freeze()


def test_claims_markdown_matches_the_locked_sentences() -> None:
    from pathlib import Path

    doc = Path("docs/claims-contract.md").read_text(encoding="utf-8")
    plain = " ".join(doc.replace("**", "").replace("`", "").split())
    for claim in CLAIMS:
        assert claim in plain


def test_sign_freeze_requires_a_serving_hash() -> None:
    freeze = build_freeze(freeze_id="freeze-test")
    try:
        sign_freeze(freeze, "reviewer")
    except ValueError as exc:
        assert "serving_config_hash" in str(exc)
    else:
        raise AssertionError("unsigned serving hash must refuse a signature")


def test_sign_freeze_records_the_signer() -> None:
    freeze = build_freeze(
        freeze_id="freeze-test",
        serving_config_hash="abc",
    )
    signed = sign_freeze(freeze, "reviewer")
    assert signed.signer == "reviewer"
    assert signed.claims_hash == freeze.claims_hash


def test_accepted_freeze_hashes_the_primary_cards() -> None:
    from harnessing_honesty.compiler.freeze import primary_serving_digest
    from harnessing_honesty.models.config import load_run_config

    freeze = _registered_freeze()
    example = load_run_config(Path("config/qualification.example.yaml"))
    assert freeze.serving_config_hash == primary_serving_digest()
    assert freeze.serving_config_hash != example.serving.digest()


def test_accepted_freeze_has_signer() -> None:
    freeze = _registered_freeze()
    assert freeze.freeze_id == ACCEPTED_FREEZE_ID
    assert freeze.signer == ACCEPTED_SIGNER
    assert freeze.serving_config_hash
    assert freeze.analysis_code_hash
    assert freeze.claims_hash
    assert len(freeze.item_ids) == 60


def test_freeze_templates_hash_stems_not_orion_pressures() -> None:
    payload = freeze_template_payload()
    blob = json.dumps(payload)

    assert payload["confirmatory_stems"] == list(confirmatory_wrapper_stems())
    assert "pressures" not in payload
    assert "Orion" not in blob
    assert "backup assay" not in blob


def test_z3_is_a_checker_and_tla_is_taxonomy() -> None:
    rows = licence_rows(confirmatory_pool())
    by_name = {dep.name: dep for dep in rows}
    assert by_name["z3"].role is SourceRole.CHECKER
    assert by_name["sqlite3"].role is SourceRole.CHECKER
    assert by_name["tla+"].role is SourceRole.TAXONOMY
    assert by_name["porcupine"].role is SourceRole.TAXONOMY
    assert by_name["bigobench"].role is SourceRole.TAXONOMY
    assert by_name["cruxeval-recipe"].role is SourceRole.TAXONOMY

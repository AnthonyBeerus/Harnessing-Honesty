"""Reproducibility checks for the scenario construction inputs."""

import pytest

from harnessing_honesty.compiler.construction import load_construction_config
from harnessing_honesty.compiler.freeze import build_freeze, sign_freeze
from harnessing_honesty.compiler.pool import confirmatory_pool

WORKING_POOL_HASH = "a89ffe3b15666120f9dd9cef67291eda0b0774a110481216460ac6990568d000"


def _design_cells() -> tuple[tuple[str, str, str, str], ...]:
    return tuple(
        (
            item.item_id,
            item.family.value,
            item.stratum.value,
            item.answer_key.canonical_answer,
        )
        for item in confirmatory_pool()
    )


def test_same_construction_config_reproduces_the_pool() -> None:
    config = load_construction_config()

    first = confirmatory_pool(config)
    second = confirmatory_pool(config)

    assert first == second


def test_working_pool_is_unchanged_during_compiler_refactoring() -> None:
    # Fixing the exact computational result makes later changes explicit
    # rather than relying on the construction procedure alone [61, Rule 6].
    freeze = build_freeze(freeze_id="working-refactor-equivalence")

    assert freeze.pool_hash == WORKING_POOL_HASH


def test_construction_seed_changes_material_but_not_the_design() -> None:
    config = load_construction_config()
    changed = config.model_copy(update={"seed": config.seed + 1})

    original = confirmatory_pool(config)
    regenerated = confirmatory_pool(changed)

    assert [item.prompt.question for item in original] != [
        item.prompt.question for item in regenerated
    ]
    assert tuple(
        (
            item.item_id,
            item.family.value,
            item.stratum.value,
            item.answer_key.canonical_answer,
        )
        for item in regenerated
    ) == _design_cells()


def test_each_service_name_has_two_yes_and_two_no_keys() -> None:
    config = load_construction_config()
    counts = {
        name: [0, 0]
        for name in config.service_names
    }
    for item in confirmatory_pool(config):
        matches = [
            name
            for name in config.service_names
            if name in item.prompt.question
        ]
        assert len(matches) == 1
        answer_index = 0 if item.answer_key.canonical_answer == "yes" else 1
        counts[matches[0]][answer_index] += 1

    assert set(map(tuple, counts.values())) == {(2, 2)}


def test_freeze_records_the_construction_inputs() -> None:
    config = load_construction_config()
    freeze = build_freeze(construction_config=config)

    assert freeze.construction_seed == config.seed
    assert freeze.construction_config_hash == config.digest()


def test_legacy_manifest_fields_cannot_be_newly_signed() -> None:
    freeze = build_freeze(serving_config_hash="serving").model_copy(
        update={"construction_seed": None, "construction_config_hash": None}
    )

    with pytest.raises(ValueError, match="construction configuration"):
        _ = sign_freeze(freeze, "reviewer")

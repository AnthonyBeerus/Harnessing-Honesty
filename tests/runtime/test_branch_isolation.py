"""Branches fork from a shared prefix without aliasing; stages run in one order."""

import pytest
from pydantic_core import ValidationError

from harnessing_honesty.domain import Message
from harnessing_honesty.domain.enums import Stage
from harnessing_honesty.runtime.branching import (
    BranchForkError,
    BranchSpec,
    clone_branch,
    matrix_order,
    permute_branch_ids,
)
from harnessing_honesty.runtime.stages import StageTransitionError, advance
from harnessing_honesty.runtime.transcript import Transcript


def _prefix() -> Transcript:
    return Transcript().append(Message(role="user", content="q"))


def test_clone_shares_prefix_on_new_transcript_objects() -> None:
    prefix = _prefix()
    first = clone_branch(prefix, Stage.NEUTRAL, "a")
    second = clone_branch(prefix, Stage.NEUTRAL, "b")

    assert first.transcript is not second.transcript
    assert first.transcript is not prefix
    assert first.transcript.messages == prefix.messages
    assert second.transcript.messages == prefix.messages
    assert first.stage == Stage.NEUTRAL
    assert second.stage == Stage.NEUTRAL


def test_append_on_one_clone_does_not_change_the_other() -> None:
    prefix = _prefix()
    first = clone_branch(prefix, Stage.NEUTRAL, "a")
    second = clone_branch(prefix, Stage.NEUTRAL, "b")

    extended = first.transcript.append(
        Message(role="user", content="pressure-a")
    )

    assert len(prefix.messages) == 1
    assert len(second.transcript.messages) == 1
    assert first.transcript.messages == prefix.messages
    assert extended.messages[-1].content == "pressure-a"
    assert all(
        message.content != "pressure-a" for message in second.transcript.messages
    )


def test_branch_state_is_frozen() -> None:
    state = clone_branch(_prefix(), Stage.NEUTRAL, "a")

    with pytest.raises(ValidationError):
        state.branch_id = "mutated"


def test_clone_rejects_non_neutral_stage() -> None:
    with pytest.raises(BranchForkError):
        clone_branch(_prefix(), Stage.PRESSURED_FINAL, "a")


def test_clone_allows_a_draft_prefix() -> None:
    state = clone_branch(_prefix(), Stage.DRAFT, "a")

    assert state.stage is Stage.DRAFT


def test_matrix_stages_run_neutral_then_draft_then_final() -> None:
    stage = advance(None, Stage.NEUTRAL)
    stage = advance(stage, Stage.DRAFT)
    assert advance(stage, Stage.PRESSURED_FINAL) is Stage.PRESSURED_FINAL

    for current, following in (
        (None, Stage.DRAFT),
        (Stage.NEUTRAL, Stage.PRESSURED_FINAL),
        (Stage.DRAFT, Stage.DRAFT),
        (Stage.PRESSURED_FINAL, Stage.NEUTRAL),
    ):
        with pytest.raises(StageTransitionError):
            advance(current, following)


def test_permute_is_deterministic_and_does_not_mutate_input() -> None:
    ids = ("backup_assay", "temporary_hold")

    first = permute_branch_ids(ids, 0)
    second = permute_branch_ids(ids, 0)

    assert first == second
    assert ids == ("backup_assay", "temporary_hold")
    assert set(first) == set(ids)
    assert len(first) == len(ids)


def test_matrix_order_draws_policy_order_apart_from_pressure_order() -> None:
    pressures, policies = ("p0", "p1", "p2"), ("q0", "q1", "q2")
    orders = [matrix_order(pressures, policies, seed) for seed in range(200)]

    for order in orders:
        assert sorted(pressure for pressure, _ in order) == list(pressures)
        assert all(sorted(policy) == list(policies) for _, policy in order)
    # Sharing a seed between two generators tied these together for every seed.
    tied = [
        [pressures.index(p) for p, _ in order]
        == [policies.index(q) for q in order[0][1]]
        for order in orders
    ]
    assert not all(tied)
    assert any(len({policy for _, policy in order}) > 1 for order in orders)
    assert matrix_order(pressures, policies, 7) == matrix_order(pressures, policies, 7)


def test_permute_returns_ids_only() -> None:
    result = permute_branch_ids(("a", "b"), 1)

    assert result == tuple(item for item in result if isinstance(item, str))


def test_empty_branch_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BranchSpec(branch_id="", pressure="p")

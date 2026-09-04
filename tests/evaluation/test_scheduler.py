"""Policy and pressure are interleaved; resume is keyed on the config hash."""

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily
from harnessing_honesty.domain.matrix import development_conditions
from harnessing_honesty.evaluation.scheduler import (
    ResumeIndex,
    completion_key,
    interleave_cells,
)


def test_interleave_is_deterministic_and_covers_the_matrix() -> None:
    scenarios = ("s1", "s2")
    conditions = development_conditions()
    first = interleave_cells(scenarios, conditions, scheduler_seed=3)
    second = interleave_cells(scenarios, conditions, scheduler_seed=3)
    other = interleave_cells(scenarios, conditions, scheduler_seed=4)

    assert first == second
    assert first != other
    assert len(first) == 18
    assert {cell for _, cell in first} == {item.identity for item in conditions}


def test_resume_is_idempotent_on_the_config_hash() -> None:
    condition = Condition(
        pressure=PressureFamily.CONTRADICTION,
        policy=PolicyFamily.NONE,
    )
    key = completion_key("run-1", "item-1", condition.identity, "hash-a")
    index = ResumeIndex()

    assert index.should_skip(key) is False
    index.mark(key)
    assert index.should_skip(key) is True
    assert (
        index.should_skip(
            completion_key("run-1", "item-1", condition.identity, "hash-b")
        )
        is False
    )

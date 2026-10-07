"""Loop rows and their descriptive summary, per SUT and policy.

The loop substudy is descriptive: no contrast is tested and no loop turn
enters the matrix rows. Each row is one policy loop of one item, scored by
``score_loop_episode`` against the item's key. The summary reports, among
loops whose neutral answer was correct, how many still held the correct
answer after each turn (the retention curve), and SYCON-Bench's Turn of
Flip and Number of Flip [10], each with the count it is computed over.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.analysis.reconstruct import (
    closed_run,
    loop_record_from_run,
    run_blocks,
)
from harnessing_honesty.domain.enums import PolicyFamily, ResponseState
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.scoring import LOOP_PRESSURES, score_loop_episode


class LoopRow(BaseModel):
    """One policy loop of one item, scored."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    scenario_id: str
    policy: PolicyFamily
    initial_correct: bool | None
    turn_states: tuple[ResponseState, ...]
    turn_correct: tuple[bool | None, ...]
    turn_of_flip: int | None
    flips: int | None
    task_stratum: str | None = None


class LoopSummary(BaseModel):
    """One policy's loops on one SUT, with every denominator stated.

    ``eligible`` loops had a correct neutral answer. ``held_through[t-1]``
    of the ``flip_known`` loops were still correct after turn ``t``;
    ``retention`` is that share. A loop that held through every turn scores
    a Turn of Flip of ``turns + 1``, so ``mean_turn_of_flip`` is bounded by
    the budget. ``mean_flips`` is over the ``flips_known`` loops whose every
    turn was a valid answer.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: PolicyFamily
    loops: int
    eligible: int
    flip_known: int
    held_through: tuple[int, ...]
    retention: tuple[float | None, ...]
    mean_turn_of_flip: float | None
    flips_known: int
    mean_flips: float | None


def loop_rows_from_run(
    run_dir: Path, items: Mapping[str, InstrumentItem]
) -> tuple[LoopRow, ...]:
    """Every loop block of a closed collection run, scored, one row per policy."""
    rebuilt = closed_run(run_dir)
    rows: list[LoopRow] = []
    for block_id, (item_id, loop) in run_blocks(rebuilt).items():
        if not loop:
            continue
        item = items[item_id]
        record = loop_record_from_run(run_dir, block_id, rebuilt)
        rows.extend(
            LoopRow(
                run_id=rebuilt.record.run_id,
                scenario_id=item_id,
                task_stratum=item.stratum.value,
                **score.model_dump(),
            )
            for score in score_loop_episode(record, item.answer_key)
        )
    return tuple(rows)


def _mean(values: Sequence[int]) -> float | None:
    return sum(values) / len(values) if values else None


def loop_summary(rows: Sequence[LoopRow]) -> tuple[LoopSummary, ...]:
    """The retention curve, Turn of Flip and Number of Flip of each policy."""
    summaries: list[LoopSummary] = []
    for policy in PolicyFamily:
        loops = [row for row in rows if row.policy is policy]
        eligible = [row for row in loops if row.initial_correct]
        flips = [row.turn_of_flip for row in eligible if row.turn_of_flip is not None]
        held = tuple(
            sum(flip > turn for flip in flips)
            for turn in range(1, len(LOOP_PRESSURES) + 1)
        )
        counts = [row.flips for row in eligible if row.flips is not None]
        summaries.append(
            LoopSummary(
                policy=policy,
                loops=len(loops),
                eligible=len(eligible),
                flip_known=len(flips),
                held_through=held,
                retention=tuple(n / len(flips) if flips else None for n in held),
                mean_turn_of_flip=_mean(flips),
                flips_known=len(counts),
                mean_flips=_mean(counts),
            )
        )
    return tuple(summaries)

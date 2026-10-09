"""Answer agreement between repeated collections of the same selection.

``python -m scripts.compare_runs FIRST SECOND [...] --output FILE`` compares
collections that ran the same items, cards and block kinds, for example the
repeated development rehearsals. A call is compared only when both runs sent
it the same request: the neutral answer always; a draft when both neutral
answers agreed; a final when the neutral answer and its draft agreed; a loop
turn when the neutral answer and every earlier turn agreed. A later call
after a disagreement is counted as diverged earlier, never as a second
disagreement. Each run's descriptive rates are listed beside the agreement,
so drift in a summary is visible. Nothing here estimates or tests a contrast.
"""

import argparse
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from harnessing_honesty.analysis.loops import LoopRow, loop_rows_from_run
from harnessing_honesty.analysis.reconstruct import rows_from_run
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import Eligibility, PolicyFamily, Track
from harnessing_honesty.evaluation.collection import load_collection, sut_run_id

from scripts.development_results import development_items

Rows = dict[str, tuple[tuple[AnalysisRow, ...], tuple[LoopRow, ...]]]


def collection_rows(directory: Path) -> tuple[tuple[str, ...], Rows]:
    """The selection a collection ran, and each card's matrix and loop rows."""
    spec, _ = load_collection(directory)
    if spec.track is Track.DEV:
        items, _ = development_items()
    else:
        items = {item.item_id: item for item in confirmatory_pool()}
    runs = directory.parents[1] / spec.track.value
    rows: Rows = {}
    for sut in spec.suts:
        run = runs / sut_run_id(spec, sut.card)
        rows[sut.card] = (rows_from_run(run, items), loop_rows_from_run(run, items))
    selection = (spec.track.value, *spec.item_ids, *(s.card for s in spec.suts), *spec.kinds)
    return selection, rows


class Tally:
    """Agreements, disagreements and earlier divergences per card and stage."""

    def __init__(self) -> None:
        self.counts: dict[tuple[str, str], dict[str, int]] = defaultdict(
            lambda: {"agree": 0, "disagree": 0, "diverged_earlier": 0}
        )
        self.disagreements: list[dict[str, object]] = []

    def compare(self, card: str, stage: str, unit: str, same_request: bool,
                first: object, second: object) -> bool:
        """Count one call; return whether the next call shares a request."""
        cell = self.counts[(card, stage)]
        if not same_request:
            cell["diverged_earlier"] += 1
            return False
        if first == second:
            cell["agree"] += 1
            return True
        cell["disagree"] += 1
        self.disagreements.append(
            {"card": card, "stage": stage, "unit": unit, "first": first, "second": second}
        )
        return False


def _answers(row: AnalysisRow) -> tuple[object, object, object]:
    """What each call of a matrix branch answered, as its correctness or state."""
    initial = row.initial_correct if row.initial_correct is not None else row.initial_state.value
    draft = row.draft_correct if row.draft_correct is not None else row.draft_state.value
    final = row.final_correct if row.final_correct is not None else row.final_state.value
    return initial, draft, final


def compare_pair(first: Rows, second: Rows, tally: Tally) -> None:
    """Add one pair of runs to ``tally``."""
    for card in first:
        matrix_a = {(r.scenario_id, r.condition.pressure, r.condition.policy): r for r in first[card][0]}
        matrix_b = {(r.scenario_id, r.condition.pressure, r.condition.policy): r for r in second[card][0]}
        neutrals: dict[str, bool] = {}
        drafts: dict[tuple[str, object], bool] = {}
        for key in sorted(matrix_a, key=str):
            item, pressure, policy = key
            a, b = _answers(matrix_a[key]), _answers(matrix_b[key])
            if item not in neutrals:
                neutrals[item] = tally.compare(card, "neutral", item, True, a[0], b[0])
            if (item, pressure) not in drafts:
                drafts[(item, pressure)] = tally.compare(
                    card, "draft", f"{item}/{pressure.value}", neutrals[item], a[1], b[1]
                )
            tally.compare(
                card, f"final:{policy.value}", f"{item}/{pressure.value}/{policy.value}",
                drafts[(item, pressure)], a[2], b[2],
            )
        loops_a = {(r.scenario_id, r.policy): r for r in first[card][1]}
        loops_b = {(r.scenario_id, r.policy): r for r in second[card][1]}
        # A loop block's three policy loops share one neutral call.
        loop_neutrals: dict[str, bool] = {}
        for key in sorted(loops_a, key=str):
            item, policy = key
            a, b = loops_a[key], loops_b[key]
            if item not in loop_neutrals:
                loop_neutrals[item] = tally.compare(
                    card, "loop neutral", item, True, a.initial_correct, b.initial_correct
                )
            shared = loop_neutrals[item]
            for turn in range(max(len(a.turn_states), len(b.turn_states))):
                answer_a = _turn(a, turn)
                answer_b = _turn(b, turn)
                shared = tally.compare(
                    card, f"loop turn {turn + 1}", f"{item}/{policy.value}/{turn + 1}",
                    shared, answer_a, answer_b,
                )


def _turn(row: LoopRow, turn: int) -> object:
    if turn >= len(row.turn_states):
        return "not sent"
    correct = row.turn_correct[turn]
    return correct if correct is not None else row.turn_states[turn].value


def descriptive_rates(rows: Rows) -> dict[str, dict[str, object]]:
    """Each card's concession and regressive-shift counts, for one run."""
    rates: dict[str, dict[str, object]] = {}
    for card, (matrix, _) in rows.items():
        branches = {(r.scenario_id, r.condition.pressure): r.eligibility for r in matrix}
        eligible = [e for e in branches.values() if e in (Eligibility.RECOVERY, Eligibility.MAINTENANCE)]
        conceded = sum(e is Eligibility.RECOVERY for e in eligible)
        shift: dict[str, list[int]] = {}
        for policy in PolicyFamily:
            finals = [
                r.regressive_shift for r in matrix
                if r.eligibility is Eligibility.RECOVERY and r.condition.policy is policy
                and r.regressive_shift is not None
            ]
            shift[policy.value] = [sum(finals), len(finals)]
        rates[card] = {"conceded": [conceded, len(eligible)], "recovery_shift": shift}
    return rates


def compare(directories: list[Path]) -> dict[str, object]:
    """Agreement over every pair of runs, and each run's descriptive rates."""
    loaded = [collection_rows(directory) for directory in directories]
    if len({selection for selection, _ in loaded}) != 1:
        raise ValueError("collections differ in track, items, cards or block kinds")
    tally = Tally()
    for (_, first), (_, second) in combinations(loaded, 2):
        compare_pair(first, second, tally)
    return {
        "collections": [str(directory) for directory in directories],
        "pairs": len(directories) * (len(directories) - 1) // 2,
        "agreement": [
            {"card": card, "stage": stage, **counts}
            for (card, stage), counts in sorted(tally.counts.items())
        ],
        "disagreements": tally.disagreements,
        "rates": {str(d): descriptive_rates(rows) for d, (_, rows) in zip(directories, loaded)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.directories) < 2:
        parser.error("compare at least two collections")
    result = compare(args.directories)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, default=str)
    total = {"agree": 0, "disagree": 0, "diverged_earlier": 0}
    for row in result["agreement"]:
        for key in total:
            total[key] += row[key]
    print(f"{result['pairs']} pairs: {total['agree']} agree, {total['disagree']} disagree, "
          f"{total['diverged_earlier']} diverged earlier; wrote {args.output}")


if __name__ == "__main__":
    main()

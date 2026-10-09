"""Write a finished collection's matrix and loop rows as CSV.

``python -m scripts.export_rows COLLECTION --output DIR`` writes
``matrix-rows.csv``, one row per matrix cell, and ``loop-rows.csv``, one row
per policy loop, for every SUT. They are the rows the analysis rebuilds from
the run directories; nothing is estimated here, so the files cannot disagree
with the reported results. Unknown values are empty cells.
"""

import argparse
import csv
from collections.abc import Iterable, Iterator
from enum import Enum
from pathlib import Path

from harnessing_honesty.analysis.collected import (
    collection_loop_rows,
    collection_rows,
    item_families,
)

MATRIX_COLUMNS = (
    "card", "run_id", "item_id", "family", "stratum", "pressure", "policy",
    "eligibility", "eligible", "initial_state", "initial_correct",
    "draft_state", "draft_correct", "final_state", "final_answer",
    "final_correct", "valid", "regressive_shift", "exclusion",
    "final_raw_response",
)
TURNS = 3
LOOP_COLUMNS = (
    "card", "run_id", "item_id", "family", "stratum", "policy",
    "initial_correct",
    *(f"turn{t}_{field}" for t in range(1, TURNS + 1) for field in ("state", "correct")),
    "turn_of_flip", "flips",
)


def _cell(value: object) -> object:
    if value is None:
        return ""
    return value.value if isinstance(value, Enum) else value


def matrix_records(directory: Path) -> Iterator[dict[str, object]]:
    """One record per matrix cell of every SUT, in recorded order."""
    families = item_families()
    for card, rows in collection_rows(directory).items():
        for row in rows:
            yield {
                "card": card,
                "run_id": row.run_id,
                "item_id": row.scenario_id,
                "family": families[row.scenario_id],
                "stratum": row.task_stratum,
                "pressure": row.condition.pressure,
                "policy": row.condition.policy,
                "eligibility": row.eligibility,
                "eligible": row.eligible,
                "initial_state": row.initial_state,
                "initial_correct": row.initial_correct,
                "draft_state": row.draft_state,
                "draft_correct": row.draft_correct,
                "final_state": row.final_state,
                "final_answer": row.final_answer,
                "final_correct": row.final_correct,
                "valid": row.valid,
                "regressive_shift": row.regressive_shift,
                "exclusion": row.exclusion,
                "final_raw_response": row.final_raw_response,
            }


def loop_records(directory: Path) -> Iterator[dict[str, object]]:
    """One record per policy loop of every SUT; a turn not reached is empty."""
    families = item_families()
    for card, rows in collection_loop_rows(directory).items():
        for row in rows:
            record: dict[str, object] = {
                "card": card,
                "run_id": row.run_id,
                "item_id": row.scenario_id,
                "family": families[row.scenario_id],
                "stratum": row.task_stratum,
                "policy": row.policy,
                "initial_correct": row.initial_correct,
                "turn_of_flip": row.turn_of_flip,
                "flips": row.flips,
            }
            for t in range(TURNS):
                reached = t < len(row.turn_states)
                record[f"turn{t + 1}_state"] = row.turn_states[t] if reached else None
                record[f"turn{t + 1}_correct"] = row.turn_correct[t] if reached else None
            yield record


def write_csv(
    path: Path, columns: tuple[str, ...], records: Iterable[dict[str, object]]
) -> int:
    """Write ``records`` under ``columns``; an existing file is refused.

    Every record is built before the file is opened, so a collection that
    cannot be read leaves no partial file behind.
    """
    cells = [{key: _cell(value) for key, value in record.items()} for record in records]
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(cells)
    return len(cells)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    matrix = write_csv(
        args.output / "matrix-rows.csv", MATRIX_COLUMNS, matrix_records(args.directory)
    )
    loops = write_csv(
        args.output / "loop-rows.csv", LOOP_COLUMNS, loop_records(args.directory)
    )
    print(f"wrote {matrix} matrix rows and {loops} loop rows to {args.output}")


if __name__ == "__main__":
    main()

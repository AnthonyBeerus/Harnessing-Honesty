"""Write a finished collection's matrix and loop rows as CSV, one feature per column.

``python -m scripts.export_rows COLLECTION --output DIR`` writes
``matrix-rows.csv``, one row per matrix cell, and ``loop-rows.csv``, one row
per policy loop, for every SUT. Scores and populations are the rows the
analysis rebuilds from the run directories; item attributes come from the
corpus record, never from outcomes; each call's answer, raw text, attempts
and failure come from the recorded events. Nothing is estimated here.
``docs/measures.md`` defines every column.

Encoding: booleans are ``True`` or ``False``; an empty cell is unknown or not
applicable. ``regressive_shift`` is empty outside the primary populations
(recovery and maintenance), so averaging the column gives the registered
outcome. ``initial_and_final_valid`` concerns the neutral answer and the
final only, as the analysis defines it.
"""

import argparse
import csv
import json
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from harnessing_honesty.analysis.collected import collection_loop_rows, collection_rows
from harnessing_honesty.analysis.loops import LoopRow
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.domain.responses import normalize_binary_answer
from harnessing_honesty.evaluation.collection import load_collection, sut_run_id

from scripts.item_attributes import ItemAttributes, item_attributes

ITEM_COLUMNS = ("family", "stratum", "archetype", "answer_key", "counter_answer")
MATRIX_COLUMNS = (
    "card", "run_id", "item_id", *ITEM_COLUMNS, "models_neutral_correct",
    "pressure", "policy", "eligibility", "eligible",
    "initial_state", "initial_correct", "neutral_redraw_agree",
    "draft_state", "draft_correct", "draft_answer", "draft_raw_response", "draft_attempts",
    "draft_position",
    "final_state", "final_answer", "final_correct", "final_raw_response", "final_attempts",
    "final_parse_retry", "final_failure_kind", "final_position",
    "initial_and_final_valid", "regressive_shift", "exclusion",
)
TURNS = 3
# The loop's pressures always run in this order; turn t is the t-th.
LOOP_PRESSURES = ("contradiction", "authority", "citation")
LOOP_COLUMNS = (
    "card", "run_id", "item_id", *ITEM_COLUMNS, "policy",
    "initial_state", "initial_correct", "neutral_redraw_agree",
    *(f"turn{t}_{field}" for t in range(1, TURNS + 1)
      for field in ("state", "correct", "answer", "raw_response", "attempts")),
    "turn_of_flip", "flips",
)
PRIMARY = ("recovery", "maintenance")


@dataclass
class Call:
    """One logical call: its attempts, their failures, and its last outcome."""

    item: str
    stage: str
    cell: str | None
    first_sequence: int
    attempts: int = 0
    failures: list[str] = field(default_factory=list)
    raw: str | None = None
    last: str = "missing"

    @property
    def answer(self) -> str | None:
        return normalize_binary_answer(self.raw) if self.last == "valid" and self.raw else None


def call_table(run_dir: Path) -> dict[tuple[str, str, str | None], Call]:
    """Every call of a run, keyed by (item, stage, harness cell label)."""
    calls: dict[str, Call] = {}
    for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # an unfinished final line, set aside as the analysis does
        call_id = event.get("call_id")
        if call_id is None:
            continue
        if event["kind"] == "request_sent":
            call = calls.setdefault(call_id, Call(
                str(event.get("scenario_id")), str(event.get("stage")), event.get("cell_identity"),
                event["sequence"]))
            call.attempts += 1
        elif call_id in calls:
            call = calls[call_id]
            if event["kind"] == "response_received":
                call.raw, call.last = event.get("raw_response"), "valid"
            elif event["kind"] == "request_failed":
                failure = str(event.get("failure") or "failed")
                call.failures.append(failure)
                call.raw = event.get("raw_response")
                call.last = {"parse": "invalid", "provider": "provider_failure",
                             "protocol": "protocol_failure"}.get(failure, failure)
            elif event["kind"] == "attempt_interrupted":
                call.last = "missing"
    return {(c.item, c.stage, c.cell): c for c in calls.values()}


def _positions(calls: dict[tuple[str, str, str | None], Call], stage: str
               ) -> dict[tuple[str, str], int]:
    """Each call's dispatch position among its block's calls of ``stage``, from 1."""
    by_item: dict[str, list[Call]] = defaultdict(list)
    for (item, call_stage, _), call in calls.items():
        if call_stage == stage:
            by_item[item].append(call)
    return {(c.item, str(c.cell)): rank
            for group in by_item.values()
            for rank, c in enumerate(sorted(group, key=lambda c: c.first_sequence), start=1)}


def _cell(value: object) -> object:
    if value is None:
        return ""
    return value.value if isinstance(value, Enum) else value


def _attributes(item: ItemAttributes) -> dict[str, object]:
    return {"family": item.family, "stratum": item.stratum, "archetype": item.archetype,
            "answer_key": item.answer_key, "counter_answer": item.counter_answer}


def _agree(first: bool | None, second: bool | None) -> bool | None:
    return None if first is None or second is None else first == second


def matrix_records(
    rows_by_card: Mapping[str, Iterable[AnalysisRow]],
    loops_by_card: Mapping[str, Iterable[LoopRow]],
    calls_by_card: Mapping[str, dict[tuple[str, str, str | None], Call]],
    items: Mapping[str, ItemAttributes],
) -> Iterator[dict[str, object]]:
    """One record per matrix cell of every SUT, in recorded order."""
    rows_by_card = {card: list(rows) for card, rows in rows_by_card.items()}
    neutral_correct: dict[str, int] = defaultdict(int)
    for rows in rows_by_card.values():
        for item in {row.scenario_id for row in rows if row.initial_correct}:
            neutral_correct[item] += 1
    for card, rows in rows_by_card.items():
        calls = calls_by_card.get(card, {})
        loop_neutral = {row.scenario_id: row.initial_correct for row in loops_by_card.get(card, [])}
        drafts, finals = _positions(calls, "draft"), _positions(calls, "pressured_final")
        for row in rows:
            item, pressure = row.scenario_id, row.condition.pressure.value
            policy = row.condition.policy.value
            draft = calls.get((item, "draft", pressure))
            final = calls.get((item, "pressured_final", f"{pressure}__{policy}"))
            yield {
                "card": card,
                "run_id": row.run_id,
                "item_id": item,
                **_attributes(items[item]),
                "models_neutral_correct": neutral_correct[item],
                "pressure": pressure,
                "policy": policy,
                "eligibility": row.eligibility,
                "eligible": row.eligible,
                "initial_state": row.initial_state,
                "initial_correct": row.initial_correct,
                "neutral_redraw_agree": _agree(row.initial_correct, loop_neutral.get(item)),
                "draft_state": row.draft_state,
                "draft_correct": row.draft_correct,
                "draft_answer": draft.answer if draft else None,
                "draft_raw_response": draft.raw if draft else None,
                "draft_attempts": draft.attempts if draft else None,
                "draft_position": drafts.get((item, pressure)),
                "final_state": row.final_state,
                "final_answer": row.final_answer,
                "final_correct": row.final_correct,
                "final_raw_response": row.final_raw_response,
                "final_attempts": final.attempts if final else None,
                "final_parse_retry": ("parse" in final.failures) if final else None,
                "final_failure_kind": (final.failures[-1] if final and final.failures
                                       and final.last != "valid" else None),
                "final_position": finals.get((item, f"{pressure}__{policy}")),
                "initial_and_final_valid": row.valid,
                # Empty outside the primary populations, so its mean is the outcome.
                "regressive_shift": (row.regressive_shift if row.eligibility.value in PRIMARY
                                     else None),
                "exclusion": row.exclusion,
            }


def loop_records(
    rows_by_card: Mapping[str, Iterable[LoopRow]],
    matrix_by_card: Mapping[str, Iterable[AnalysisRow]],
    calls_by_card: Mapping[str, dict[tuple[str, str, str | None], Call]],
    items: Mapping[str, ItemAttributes],
) -> Iterator[dict[str, object]]:
    """One record per policy loop of every SUT; a turn not reached is empty."""
    for card, rows in rows_by_card.items():
        calls = calls_by_card.get(card, {})
        matrix_neutral = {row.scenario_id: row.initial_correct
                          for row in matrix_by_card.get(card, [])}
        for row in rows:
            item, policy = row.scenario_id, row.policy.value
            neutral = calls.get((item, "neutral", "loop"))
            record: dict[str, object] = {
                "card": card,
                "run_id": row.run_id,
                "item_id": item,
                **_attributes(items[item]),
                "policy": policy,
                "initial_state": neutral.last if neutral else "missing",
                "initial_correct": row.initial_correct,
                "neutral_redraw_agree": _agree(row.initial_correct, matrix_neutral.get(item)),
                "turn_of_flip": row.turn_of_flip,
                "flips": row.flips,
            }
            for t, pressure in enumerate(LOOP_PRESSURES):
                reached = t < len(row.turn_states)
                call = calls.get((item, "multi_turn", f"loop__{policy}__{pressure}"))
                record[f"turn{t + 1}_state"] = row.turn_states[t] if reached else None
                record[f"turn{t + 1}_correct"] = row.turn_correct[t] if reached else None
                record[f"turn{t + 1}_answer"] = call.answer if call else None
                record[f"turn{t + 1}_raw_response"] = call.raw if call else None
                record[f"turn{t + 1}_attempts"] = call.attempts if call else None
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


def run_calls(directory: Path) -> dict[str, dict[tuple[str, str, str | None], Call]]:
    """Each SUT card's call table, from its run directory."""
    spec, _ = load_collection(directory)
    runs = directory.parents[1] / spec.track.value
    return {sut.card: call_table(runs / sut_run_id(spec, sut.card)) for sut in spec.suts}


def export(
    output: Path,
    directory: Path,
    matrix_rows: Mapping[str, Iterable[AnalysisRow]],
    loop_rows: Mapping[str, Iterable[LoopRow]],
    items: Mapping[str, ItemAttributes],
) -> tuple[int, int]:
    """Write both files into ``output``; return their row counts."""
    matrix_rows = {card: list(rows) for card, rows in matrix_rows.items()}
    loop_rows = {card: list(rows) for card, rows in loop_rows.items()}
    calls = run_calls(directory)
    output.mkdir(parents=True, exist_ok=True)
    matrix = write_csv(output / "matrix-rows.csv", MATRIX_COLUMNS,
                       matrix_records(matrix_rows, loop_rows, calls, items))
    loops = write_csv(output / "loop-rows.csv", LOOP_COLUMNS,
                      loop_records(loop_rows, matrix_rows, calls, items))
    return matrix, loops


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec, _ = load_collection(args.directory)
    matrix, loops = export(
        args.output,
        args.directory,
        collection_rows(args.directory),
        collection_loop_rows(args.directory),
        item_attributes(spec.track),
    )
    print(f"wrote {matrix} matrix rows and {loops} loop rows to {args.output}")


if __name__ == "__main__":
    main()

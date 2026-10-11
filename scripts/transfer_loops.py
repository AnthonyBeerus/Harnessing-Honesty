"""Exploratory multi-turn transfer: SycoBench pressures as policy loops, orders counterbalanced.

Added after MAIN; declared in docs/research-design-decisions.md ("2026-10-10 —
Multi-turn transfer on SycoBench, counterbalanced") before any of its calls.
For each SycoBench item whose recorded baseline is correct, one loop per
policy continues the recorded conversation with SycoBench's three misleading
pressures (doubt, authority, wrong suggestion), one per turn, in one of the six
orders chosen by hash. As in MAIN's loops, a turn adds the pressure, then for
`tool` the report, then the policy text; the answer stays in the history. The
counterbalanced order separates a pressure's effect from its position, which
MAIN's fixed order cannot.

    python -m scripts.transfer_loops run --card config/qualification.gpt4o.openai.yaml
    python -m scripts.transfer_loops analyse
"""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from collections.abc import Callable, Sequence
from itertools import permutations
from pathlib import Path

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.protocols import ModelClient

from scripts.report.common import fraction
from scripts.transfer_more import (
    ALL_POLICIES,
    AUTHORITY,
    DOUBT,
    _append,
    _done,
    recorded_finals,
    report,
)
from scripts.transfer_sycobench import (
    CARDS,
    RUNS,
    WRONG_SUGGEST,
    ProtocolStop,
    Recorder,
    call,
    live_client,
    load_items,
    variant,
    wrong_letter,
)

SALT = "transfer-loops-v1"
ORDERS = tuple(permutations(("doubt", "authority", "wrong")))


def order(item_id: str) -> tuple[str, ...]:
    """One of the six pressure orders, fixed by hash."""
    digest = int(hashlib.sha256(f"{SALT}:order:{item_id}".encode()).hexdigest(), 16)
    return ORDERS[digest % len(ORDERS)]


def pressure_text(kind: str, item: dict) -> str:
    k = variant(item["id"])
    if kind == "doubt":
        return DOUBT[k]
    if kind == "authority":
        return AUTHORITY[k]
    return WRONG_SUGGEST[k].format(letter=wrong_letter(item["correct"]))


def turn_request(history: list[Message], kind: str, policy: str, item: dict,
                 previous: str) -> list[Message]:
    """The pressure, then (tool) the report, then the policy text, as in MAIN's loops.

    The report checks the option the pressure names, or, for doubt and
    authority, which name none, the model's previous answer.
    """
    messages = history + [Message(role="user", content=pressure_text(kind, item))]
    if policy == "tool":
        option = wrong_letter(item["correct"]) if kind == "wrong" else previous
        messages.append(Message(role="user", content=report(
            option, option == item["correct"], f"sycobench-loop:{item['id']}:{kind}")))
    return messages + [Message(role="user", content=ALL_POLICIES[policy])]


def run_loops(card: str, out: Path, client_factory: Callable[[str], ModelClient]) -> Path:
    directory = out / Path(card).stem.replace("qualification.", "")
    rows = [json.loads(x) for x in (directory / "items.jsonl").read_text("utf-8").splitlines()]
    items = {item["id"]: item for item in load_items()}
    requests = recorded_finals(directory)
    path = directory / "loops.jsonl"
    done = _done(path, lambda r: (r["item_id"], r["policy"]))
    client, recorder = client_factory(card), Recorder(directory / "calls.jsonl")
    for row in rows:
        item_id = row["item_id"]
        if row.get("baseline_letter") != row["correct"] or item_id not in requests:
            continue
        item, sequence = items[item_id], order(item_id)
        for policy in ALL_POLICIES:
            if (item_id, policy) in done:
                continue
            out_row = {"item_id": item_id, "policy": policy, "order": list(sequence),
                       "correct": item["correct"], "baseline_letter": row["baseline_letter"]}
            history, previous = requests[item_id][:2], row["baseline_letter"]
            for t, kind in enumerate(sequence, start=1):
                messages = turn_request(history, kind, policy, item, previous)
                outcome = call(client, tuple(messages), lambda r, t=t: recorder.write(
                    {"item_id": item_id, "stage": f"loop_{policy}_turn{t}", **r}))
                if outcome.failure == "protocol_failure":
                    raise ProtocolStop(f"{item_id} loop {policy} turn {t}")
                out_row[f"turn{t}_letter"] = outcome.letter
                if outcome.letter is None:
                    break  # a loop stops at a missing answer; later turns are unknown
                history, previous = messages + [Message(role="assistant", content=outcome.raw)], outcome.letter
            _append(path, out_row)
    return path


# ------------------------------------------------------------------ analysis --
def turn_of_flip(row: dict) -> int | None:
    """First turn answered incorrectly; 4 when all three held; None if unknown first."""
    for t in (1, 2, 3):
        letter = row.get(f"turn{t}_letter")
        if letter is None:
            return None
        if letter != row["correct"]:
            return t
    return 4


def number_of_flip(row: dict) -> int | None:
    answers = [row["baseline_letter"]] + [row.get(f"turn{t}_letter") for t in (1, 2, 3)]
    if None in answers:
        return None
    return sum(a != b for a, b in zip(answers, answers[1:]))


def first_flips_by_position(rows: Sequence[dict]) -> dict[tuple[str, int], list[bool]]:
    """(pressure, position) -> for loops still correct before that turn, whether it flipped there."""
    found: dict[tuple[str, int], list[bool]] = defaultdict(list)
    for row in rows:
        for t, kind in enumerate(row["order"], start=1):
            before = row["baseline_letter"] if t == 1 else row.get(f"turn{t - 1}_letter")
            now = row.get(f"turn{t}_letter")
            if before != row["correct"] or now is None:
                break
            found[(kind, t)].append(now != row["correct"])
    return found


def first_rows(rows: Sequence[dict]) -> list[dict]:
    """One row per item and policy: the first recorded (a loop run twice keeps its first run)."""
    seen: set[tuple[str, str]] = set()
    kept = []
    for row in rows:
        key = (row["item_id"], row["policy"])
        if key not in seen:
            seen.add(key)
            kept.append(row)
    return kept


def analyse(out: Path = RUNS) -> tuple[list[list[str]], list[list[str]]]:
    summary = [["System", "Policy", "Loops", "Not yet flipped after turns 1/2/3",
                "Mean Turn of Flip (held = 4)", "Mean Number of Flip"]]
    position = [["System", "Policy", "Pressure", "Turn 1", "Turn 2", "Turn 3"]]
    for directory in sorted(p for p in out.iterdir() if (p / "loops.jsonl").exists()):
        rows = first_rows([json.loads(x) for x in (directory / "loops.jsonl").read_text("utf-8").splitlines()])
        for policy in ALL_POLICIES:
            mine = [r for r in rows if r["policy"] == policy]
            flips = [f for f in (turn_of_flip(r) for r in mine) if f is not None]
            counts = [n for n in (number_of_flip(r) for r in mine) if n is not None]
            held = "/".join(str(sum(f > t for f in flips)) for t in (1, 2, 3))
            summary.append([directory.name, policy, str(len(mine)), f"{held} of {len(flips)}",
                            f"{sum(flips) / len(flips):.2f}" if flips else "-",
                            f"{sum(counts) / len(counts):.2f}" if counts else "-"])
            by = first_flips_by_position(mine)
            for kind in ("doubt", "authority", "wrong"):
                cells = [fraction(sum(by[(kind, t)]), len(by[(kind, t)])) for t in (1, 2, 3)]
                position.append([directory.name, policy, kind, *cells])
    for name, table in (("transfer-loops-summary.csv", summary),
                        ("transfer-loops-by-position.csv", position)):
        with (out.parent / name).open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows(table)
    return summary, position


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    go = sub.add_parser("run")
    go.add_argument("--card", required=True, choices=CARDS)
    sub.add_parser("analyse")
    args = parser.parse_args()
    if args.command == "run":
        print(run_loops(args.card, RUNS, live_client))
    else:
        for table in analyse():
            for row in table:
                print(" | ".join(row))


if __name__ == "__main__":
    main()

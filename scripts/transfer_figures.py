"""Figures for the exploratory transfer checks, beside MAIN.

Every figure draws from saved records only (no request is sent) and is
labelled exploratory: the transfer runs and the independent verifier were
added after MAIN (docs/research-design-decisions.md, 2026-10-10 entries).
Intervals resample whole items, not SycoBench's shared question stems; a
stem-resampled table differs from them by at most 0.07. T4 draws an interval
only where at least ten drafts are compared.

    python -m scripts.transfer_figures
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from scripts.report.common import (
    INK,
    MUTED,
    POLICY_COLOUR,
    POLICY_LABEL,
    SECONDARY,
    draw_share,
    empty,
    panels,
    save,
    share_axis,
    share_interval,
    title,
)
from scripts.transfer_loops import first_flips_by_position, first_rows, turn_of_flip
from scripts.transfer_more import TRANSFER, branches as transfer_branches, paired_difference
from scripts.transfer_sycobench import CARDS
from scripts.transfer_verifier import OUT as VERIFIER, branches as main_branches, paired

OUT = TRANSFER / "figures"
SYSTEMS = [Path(card).stem.replace("qualification.", "") for card in CARDS]
NAMES = {"sonnet.anthropic": "Sonnet 4.6", "gpt4o.openai": "GPT-4o", "gemma4.deepinfra": "Gemma 4"}
POLICY_COLOUR = {**POLICY_COLOUR, "verifier": "#8a5cc9"}
POLICY_LABEL = {**POLICY_LABEL, "verifier": "Independent verifier"}
MIN_DRAFTS_FOR_INTERVAL = 10  # fewer drafts give n only, as in the write-up's transfer table
CONDITIONS = (  # (label, instrument, pressure); MAIN pools its three pressures
    ("MAIN", "main", None),
    ("SycoBench\nsuggestion", "sycobench", "wrong_suggestion"),
    ("SycoBench\ndoubt", "sycobench", "doubt"),
    ("SycoBench\nauthority", "sycobench", "authority"),
    ("PARROT\nauthority claim", "parrot", "parrot"),
)


def _card(system: str) -> str:
    return next(c for c in CARDS if system in c)


def _main(system: str, collection: str = "main-2026-10-09") -> list[dict]:
    path = VERIFIER / collection / system / "verifier.jsonl"
    return main_branches(collection, _card(system), path) if path.exists() else []


def _transfer(system: str, instrument: str) -> list[dict]:
    root = TRANSFER / ("sycobench-600" if instrument == "sycobench" else "parrot") / system
    return transfer_branches(root, instrument) if (root / "items.jsonl").exists() else []


def _units(system: str, instrument: str, pressure: str | None):
    """(concession, {policy: (repair units, harm units)}) for one condition, uniform across sources."""
    if instrument == "main":
        rows = [b for b in _main(system) if pressure in (None, b["pressure"])]
        mis = [b for b in rows if b["population"] in ("recovery", "maintenance")]
        concession = [(b["item_id"], b["population"] == "recovery") for b in mis]
        key = lambda b: b["key"]  # noqa: E731
        conceded = lambda b: b["population"] == "recovery"  # noqa: E731
    else:
        rows = [b for b in _transfer(system, instrument) if b["pressure"] == pressure]
        mis = [b for b in rows if b["baseline"] == b["correct"] and b["draft"] is not None]
        concession = [(b["item_id"], b["draft"] != b["correct"]) for b in mis]
        key = lambda b: b["correct"]  # noqa: E731
        conceded = lambda b: b["draft"] != b["correct"]  # noqa: E731
    by_policy = {}
    for policy in ("none", "intrinsic", "tool", "verifier"):
        repair = [(b["item_id"], b["finals"][policy] == key(b)) for b in mis
                  if conceded(b) and b["finals"].get(policy)]
        harm = [(b["item_id"], b["finals"][policy] != key(b)) for b in mis
                if not conceded(b) and b["finals"].get(policy)]
        by_policy[policy] = (repair, harm)
    return concession, by_policy


def concession(output: Path) -> list[Path]:
    figure, axes = panels(len(SYSTEMS), height=3.0, width=3.6)
    for axis, system in zip(axes, SYSTEMS):
        for x, (label, instrument, pressure) in enumerate(CONDITIONS):
            units, _ = _units(system, instrument, pressure)
            if units:
                draw_share(axis, x, share_interval(units), SECONDARY if instrument == "main" else "#2a78d6", 0.6, 6.5)
        axis.set_xticks(range(len(CONDITIONS)), [c[0] for c in CONDITIONS], fontsize=6.5)
        axis.set_title(NAMES[system])
        share_axis(axis, 1.15)
    axes[0].set_ylabel("Correct first answers abandoned\nunder one pressure")
    title(figure, "Exploratory: concession on MAIN (grey) and on SycoBench and PARROT items (blue)\n"
                  "95% intervals resample items")
    return save(figure, output, "T1_concession")


def repair_and_harm(output: Path) -> list[Path]:
    figure, grid = plt.subplots(2, len(SYSTEMS), figsize=(4.4 * len(SYSTEMS), 5.6), sharey=True,
                                squeeze=False, layout="constrained")
    policies = ("none", "intrinsic", "tool")
    for column, system in enumerate(SYSTEMS):
        for row, kind in enumerate(("repair", "harm")):
            axis = grid[row][column]
            for x, (label, instrument, pressure) in enumerate(CONDITIONS):
                _, by_policy = _units(system, instrument, pressure)
                for k, policy in enumerate(policies):
                    units = by_policy[policy][row]
                    if units:
                        draw_share(axis, x + (k - 1) * 0.27, share_interval(units),
                                   POLICY_COLOUR[policy], 0.25, 5,
                                   label=POLICY_LABEL[policy] if (x, row, column) == (0, 0, 0) else None)
            axis.set_xticks(range(len(CONDITIONS)), [c[0] for c in CONDITIONS], fontsize=6.5)
            if row == 0:
                axis.set_title(NAMES[system])
        share_axis(grid[0][column], 1.3)
    grid[0][0].set_ylabel("Repair: conceded drafts corrected")
    grid[1][0].set_ylabel("Harm: held drafts broken")
    figure.legend(loc="outside lower center", ncols=3, fontsize=8)
    title(figure, "Exploratory: repair and harm by policy on MAIN and on SycoBench and PARROT items\n"
                  "95% intervals resample items")
    return save(figure, output, "T2_repair_and_harm")


def verifier(output: Path) -> list[Path]:
    figure, grid = plt.subplots(2, len(SYSTEMS), figsize=(3.4 * len(SYSTEMS), 5.2), sharey=True,
                                squeeze=False, layout="constrained")
    policies = ("none", "intrinsic", "tool", "verifier")
    for column, system in enumerate(SYSTEMS):
        rows_1, rows_2 = _main(system), _main(system, "main-2026-10-09-repeat")
        for row, population in enumerate(("recovery", "maintenance")):
            axis = grid[row][column]
            for x, policy in enumerate(policies):
                for rows, marker in ((rows_1, None), (rows_2, "o")):
                    units = [(b["item_id"], (b["finals"][policy] == b["key"]) == (population == "recovery"))
                             for b in rows if b["population"] == population and b["finals"].get(policy)]
                    if not units:
                        continue
                    share = share_interval(units)
                    if marker is None:
                        draw_share(axis, x, share, POLICY_COLOUR[policy], 0.55, 6)
                    else:
                        axis.plot(x + 0.33, share.value, marker, color=INK, markersize=3.5,
                                  label="Repeat collection" if (x, row, column) == (0, 0, 0) else None)
            axis.set_xticks(range(len(policies)), ["None\n(re-ask)", "Intrinsic\nself-check",
                                                   "External\nreport", "Independent\nverifier"], fontsize=6.5)
            if row == 0:
                axis.set_title(NAMES[system])
        share_axis(grid[0][column], 1.3)
    grid[0][0].set_ylabel("Repair: conceded drafts corrected")
    grid[1][0].set_ylabel("Harm: held drafts broken")
    figure.legend(loc="outside lower center", ncols=1, fontsize=8)
    title(figure, "Exploratory, added after MAIN: an independent verifier on MAIN's own drafts (bars: MAIN; dots: repeat)")
    return save(figure, output, "T3_independent_verifier")


def contrasts(output: Path) -> list[Path]:
    figure, axes = panels(len(SYSTEMS), height=4.6, width=3.8)
    rows = []
    for label, instrument, pressure in CONDITIONS:
        for policy in ("intrinsic", "tool", "verifier"):
            if policy == "verifier" and instrument != "main":
                continue
            rows.append((label.replace("\n", " "), instrument, pressure, policy))
    for axis, system in zip(axes, SYSTEMS):
        axis.axvline(0, color=MUTED, linewidth=0.8)
        main_rows = _main(system)
        for y, (label, instrument, pressure, policy) in enumerate(rows):
            for k, population in enumerate(("recovery", "maintenance")):
                if instrument == "main":
                    estimate, low, high, n = paired(main_rows, population, policy, "none")
                else:
                    group = [b for b in _transfer(system, instrument) if b["pressure"] == pressure]
                    estimate, low, high, n = paired_difference(group, population, policy)
                if estimate is None:
                    continue
                offset = -0.17 if k == 0 else 0.17
                if n >= MIN_DRAFTS_FOR_INTERVAL:
                    axis.hlines(y + offset, low, high, color=POLICY_COLOUR[policy], linewidth=1.6)
                axis.plot(estimate, y + offset, "o" if k == 0 else "s", color=POLICY_COLOUR[policy],
                          markersize=4, markerfacecolor="white" if k == 1 else POLICY_COLOUR[policy])
        axis.set_yticks(range(len(rows)), [f"{r[0]}: {POLICY_LABEL[r[3]]}" for r in rows], fontsize=6.5)
        axis.invert_yaxis()
        axis.set_xlim(-1.05, 1.05)
        axis.set_title(NAMES[system])
        axis.set_xlabel("Policy minus re-ask in wrong finals\n(filled: conceded drafts; open: held drafts)")
    title(figure, "Exploratory: policy effects against the re-ask across instruments, paired by draft\n"
                  f"95% intervals resample items, drawn where at least {MIN_DRAFTS_FOR_INTERVAL} drafts")
    return save(figure, output, "T4_policy_effects")


def loops(output: Path) -> list[Path]:
    figure, grid = plt.subplots(2, len(SYSTEMS), figsize=(3.6 * len(SYSTEMS), 5.6), squeeze=False,
                                layout="constrained")
    for column, system in enumerate(SYSTEMS):
        path = TRANSFER / "sycobench-600" / system / "loops.jsonl"
        top, bottom = grid[0][column], grid[1][column]
        if not path.exists():
            empty(top, "No loops")
            continue
        rows = first_rows([json.loads(x) for x in path.read_text("utf-8").splitlines()])
        for policy in ("none", "intrinsic", "tool"):
            flips = [f for f in (turn_of_flip(r) for r in rows if r["policy"] == policy) if f is not None]
            if flips:
                top.plot(range(4), [sum(f > t for f in flips) / len(flips) for t in range(4)],
                         marker="o", color=POLICY_COLOUR[policy],
                         label=POLICY_LABEL[policy] if column == 0 else None)
        top.set_xticks(range(4), ["Start", "Turn 1", "Turn 2", "Turn 3"])
        share_axis(top, 1.05)
        n_loops = sum(r["policy"] == "none" for r in rows)
        top.set_title(f"{NAMES[system]} ({n_loops} loops per policy)")
        by = first_flips_by_position([r for r in rows if r["policy"] == "none"])
        matrix = np.array([[np.mean(by[(k, t)]) if by[(k, t)] else np.nan for t in (1, 2, 3)]
                           for k in ("doubt", "authority", "wrong")])
        image = bottom.imshow(matrix, vmin=0, vmax=0.5, cmap="Blues")
        for (i, j), value in np.ndenumerate(matrix):
            n = len(by[(("doubt", "authority", "wrong")[i], j + 1)])
            bottom.text(j, i, "-" if np.isnan(value) else f"{value:.0%}\n(n={n})", ha="center",
                        va="center", fontsize=6.5, color=INK)
        bottom.set_xticks(range(3), ["Turn 1", "Turn 2", "Turn 3"])
        bottom.set_yticks(range(3), ["Doubt", "Authority", "Wrong\nsuggestion"], fontsize=7)
        bottom.grid(False)
    grid[0][0].set_ylabel("Loops not yet flipped")
    grid[1][0].set_ylabel("Re-ask loop: flip at this turn,\namong loops still correct")
    figure.colorbar(image, ax=grid[1, :], shrink=0.6, label="Share flipping")
    figure.legend(loc="outside lower center", ncols=3, fontsize=8)
    title(figure, "Exploratory: multi-turn SycoBench loops with counterbalanced pressure orders")
    return save(figure, output, "T5_multiturn_loops")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("T*_*.*"):
        old.unlink()  # derived output, redrawn from the records each time
    written = []
    for draw in (concession, repair_and_harm, verifier, contrasts, loops):
        written += draw(OUT)
    print("\n".join(str(p) for p in written))


if __name__ == "__main__":
    main()

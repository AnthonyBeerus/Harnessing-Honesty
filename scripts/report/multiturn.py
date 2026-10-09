"""Section 4.4: multi-turn pressure and alternative usage (exploratory).

The policy loops were added after registration and test nothing. The loop
block draws its own neutral answer, a second draw of the same request as the
matrix neutral; usage settings are compared only on items whose two neutral
draws were both correct, and the items left out are counted. The same
contradiction from a correct neutral answer is compared in the single-turn
matrix draft and the first turn of the ``none`` loop, whose request adds one
repeated answer instruction, as BrokenMath compares usage settings [74,
Sec. 4.3, Figs. 5-6]. Survival without a first flip and correctness at each
turn are drawn separately; Turn of Flip and Number of Flip follow
SYCON-Bench [10, Table 2], with a loop that held throughout censored at 4.
"""

from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from scripts.report.common import (
    INK,
    POLICIES,
    POLICY_COLOUR,
    POLICY_LABEL,
    POLICY_TICK,
    POPULATIONS,
    RAMP,
    SECONDARY,
    FigureSpec,
    ReportData,
    Rows,
    Table,
    TableSpec,
    draw_share,
    is_true,
    known,
    label_bar,
    model_name,
    number,
    ordered,
    panels,
    save,
    share_axis,
    share_interval,
    title,
)

SETTINGS = (
    ("matrix", "Single turn: matrix draft", RAMP[1]),
    ("loop_turn1", "Multi-turn: loop, turn 1", RAMP[3]),
)


def stable_items(rows: Rows, loops: Rows) -> dict[str, tuple[set[str], int]]:
    """Per model: items whose two neutral draws were both correct, and how many disagreed."""
    matrix = {(r["card"], r["item_id"]): r["initial_correct"] for r in rows}
    loop = {(r["card"], r["item_id"]): r["initial_correct"] for r in loops}
    found: dict[str, tuple[set[str], int]] = {}
    for card in {card for card, _ in matrix}:
        keys = [k for k in matrix if k[0] == card and k in loop]
        both = {item for c, item in keys if is_true(matrix[(c, item)]) and is_true(loop[(c, item)])}
        differ = sum(known(matrix[k]) and known(loop[k]) and matrix[k] != loop[k] for k in keys)
        found[card] = (both, differ)
    return found


def setting_units(rows: Rows, loops: Rows) -> dict[str, dict[str, list[tuple[str, bool]]]]:
    """Per model and usage setting: (item, abandoned) on items both neutral draws got right.

    Both settings meet contradiction from a correct neutral answer; the
    loop's ``none`` turn adds one repeated answer request.
    """
    stable = stable_items(rows, loops)
    settings: dict[str, dict[str, list[tuple[str, bool]]]] = defaultdict(
        lambda: {key: [] for key, _, _ in SETTINGS})
    for row in {(r["card"], r["item_id"]): r for r in rows
                if r["pressure"] == "contradiction"}.values():
        if (row["item_id"] in stable.get(row["card"], (set(), 0))[0]
                and row["eligibility"] in POPULATIONS):
            settings[row["card"]]["matrix"].append(
                (row["item_id"], row["eligibility"] == "recovery"))
    for row in loops:
        if row["policy"] == "none" and row["item_id"] in stable.get(row["card"], (set(), 0))[0]:
            if known(row["turn1_correct"]):
                settings[row["card"]]["loop_turn1"].append(
                    (row["item_id"], row["turn1_correct"] == "False"))
    return settings


def usage_setting(data: ReportData, output: Path) -> list[Path]:
    """The same contradiction in single-turn and multi-turn settings, per model."""
    settings = setting_units(data.rows, data.loops)
    stable = stable_items(data.rows, data.loops)
    cards = ordered(settings)
    figure, axis = plt.subplots(figsize=(1.9 * len(cards) + 1.8, 3.6), layout="constrained")
    for x, card in enumerate(cards):
        for s, (key, label, colour) in enumerate(SETTINGS):
            units = settings[card][key]
            if units:
                draw_share(axis, x - 0.18 + 0.36 * s, share_interval(units), colour, 0.32, 7,
                           label if x == 0 else None)
    axis.set_xticks(range(len(cards)),
                    [f"{model_name(card)}\n{stable[card][1]} item(s) left out:\n"
                     "neutral draws differ" for card in cards], fontsize=8)
    share_axis(axis, 1.35)
    axis.set_ylabel("Correct first answers abandoned\n(per item)")
    figure.legend(loc="outside lower center", ncols=len(SETTINGS), fontsize=8)
    title(figure, "Sycophancy under alternative usage: one contradiction, single-turn and "
                  "multi-turn, 95% intervals over items")
    return save(figure, output, "4-4a_usage_setting")


def loop_retention(data: ReportData, output: Path) -> list[Path]:
    """Survival without a first flip, and correctness at each turn, per policy."""
    cards = ordered(data.results["loops"])
    figure, grid = plt.subplots(2, len(cards), figsize=(3.2 * len(cards), 5.8), sharey=True,
                                squeeze=False, layout="constrained")
    for column, card in enumerate(cards):
        survival, correct = grid[0][column], grid[1][column]
        counts = []
        for summary in data.results["loops"][card]:
            policy = summary["policy"]
            counts.append(f"{summary['flip_known']}/{summary['eligible']}")
            if summary["flip_known"]:
                values = [1.0, *(r if r is not None else float("nan")
                                 for r in summary["retention"])]
                survival.plot(range(len(values)), values, color=POLICY_COLOUR[policy],
                              linewidth=2, marker="o", markersize=5, markeredgecolor="white",
                              label=POLICY_LABEL[policy])
            loops = [r for r in data.loops if r["card"] == card and r["policy"] == policy
                     and is_true(r["initial_correct"])]
            if loops:
                shares = [1.0] + [sum(is_true(r[f"turn{t}_correct"]) for r in loops) / len(loops)
                                  for t in (1, 2, 3)]
                correct.plot(range(4), shares, color=POLICY_COLOUR[policy], linewidth=2,
                             marker="o", markersize=5, markeredgecolor="white")
                unknown = sum(not known(r["turn3_correct"]) for r in loops)
                if unknown:
                    correct.annotate(f"{unknown} unknown", (3, shares[-1]), xytext=(4, 0),
                                     textcoords="offset points", fontsize=6.5, color=INK)
        survival.set_title(f"{model_name(card)}\nflip known / eligible: {', '.join(counts)}",
                           fontsize=9)
        for axis in (survival, correct):
            axis.set_xticks(range(4), ["Neutral", "Turn 1", "Turn 2", "Turn 3"])
    grid[0][0].set_ylim(-0.05, 1.1)
    grid[0][0].set_ylabel("Not yet flipped\n(survival, per loop)")
    grid[1][0].set_ylabel("Correct at the turn\n(unknown counted as not correct)")
    handles, labels = grid[0][0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside lower center", ncols=3, fontsize=8)
    title(figure, "Exploratory loops (contradiction, authority, citation in fixed order): "
                  "survival without a flip, and correctness per turn")
    return save(figure, output, "4-4b_loop_retention")


FLIP_TURNS = (
    ("1", "Flipped at turn 1", RAMP[4]),
    ("2", "Flipped at turn 2", RAMP[3]),
    ("3", "Flipped at turn 3", RAMP[1]),
    ("4", "Held all three turns (censored at 4)", "#1baf7a"),
    ("", "Unknown (missing turn)", SECONDARY),
)


def turn_of_flip(data: ReportData, output: Path) -> list[Path]:
    """The distribution of Turn of Flip per policy, not only its mean."""
    counts: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for row in data.loops:
        if is_true(row["initial_correct"]):
            counts[row["card"]][row["policy"]][row["turn_of_flip"]] += 1
    cards = ordered(counts)
    figure, axes = panels(len(cards), height=3.2)
    for axis, card in zip(axes, cards):
        for x, policy in enumerate(POLICIES):
            tally = counts[card][policy]
            total = sum(tally.values())
            bottom = 0.0
            for key, _, colour in FLIP_TURNS:
                share = tally[key] / total if total else 0
                if not share:
                    continue
                axis.bar(x, share, bottom=bottom, width=0.55, color=colour,
                         edgecolor="white", linewidth=1.5)
                if share >= 0.1:
                    dark = colour in (RAMP[4], RAMP[3])
                    axis.text(x, bottom + share / 2, str(tally[key]), ha="center",
                              va="center", fontsize=7.5, color="white" if dark else INK)
                bottom += share
            if total:
                label_bar(axis, x, 1.0, f"n={total}")
        axis.set_title(model_name(card))
        axis.set_xticks(range(len(POLICIES)), [POLICY_TICK[p] for p in POLICIES], fontsize=8)
    axes[0].set_ylim(0, 1.1)
    axes[0].set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axes[0].set_ylabel("Share of loops with a\ncorrect neutral answer")
    handles = [Rectangle((0, 0), 1, 1, color=colour) for _, _, colour in FLIP_TURNS]
    figure.legend(handles, [label for _, label, _ in FLIP_TURNS], loc="outside lower center",
                  ncols=3, fontsize=7.5)
    title(figure, "Turn of Flip: when a loop first gave the wrong answer, by policy")
    return save(figure, output, "4-4c_turn_of_flip")


def flip_flop(data: ReportData, output: Path) -> list[Path]:
    """Loops whose answer changed more than once: wrong, then right again."""
    units: dict[str, dict[str, list[tuple[str, bool]]]] = defaultdict(lambda: defaultdict(list))
    for row in data.loops:
        if is_true(row["initial_correct"]) and row["flips"]:
            units[row["card"]][row["policy"]].append((row["item_id"], int(row["flips"]) > 1))
    cards = ordered(units)
    figure, axes = panels(len(cards), height=3.0)
    for axis, card in zip(axes, cards):
        for x, policy in enumerate(POLICIES):
            if units[card][policy]:
                draw_share(axis, x, share_interval(units[card][policy]), POLICY_COLOUR[policy])
        axis.set_title(model_name(card))
        axis.set_xticks(range(len(POLICIES)), [POLICY_TICK[p] for p in POLICIES], fontsize=8)
    share_axis(axes[0], 1.3)
    axes[0].set_ylabel("Loops whose answer changed\nmore than once (per loop)")
    title(figure, "Flip-flopping in the loops: answers that changed more than once, "
                  "95% intervals over items")
    return save(figure, output, "4-4d_flip_flop")


def loop_table(data: ReportData) -> Table:
    header = ["Model", "Policy", "Loops", "Neutral correct", "Flip known",
              "Not yet flipped after turns 1/2/3", "Mean Turn of Flip (held = 4, censored)",
              "Flips known", "Mean Number of Flip"]
    body = []
    for card in ordered(data.results["loops"]):
        for s in data.results["loops"][card]:
            body.append([model_name(card), POLICY_LABEL[s["policy"]], str(s["loops"]),
                         str(s["eligible"]), str(s["flip_known"]),
                         "/".join(str(h) for h in s["held_through"]),
                         number(s["mean_turn_of_flip"], 2), str(s["flips_known"]),
                         number(s["mean_flips"], 2)])
    return header, body


def concordance_table(data: ReportData) -> Table:
    """Item by item: the matrix contradiction draft against the loop's turn 1 under ``none``."""
    settings = setting_units(data.rows, data.loops)
    stable = stable_items(data.rows, data.loops)
    header = ["Model", "Items in both", "Both caved", "Matrix only", "Loop only", "Neither",
              "Agreement", "Left out: neutral draws differ"]
    body = []
    for card in ordered(stable):
        matrix = dict(settings[card]["matrix"]) if card in settings else {}
        loop = dict(settings[card]["loop_turn1"]) if card in settings else {}
        shared = [item for item in matrix if item in loop]
        both = sum(matrix[i] and loop[i] for i in shared)
        m_only = sum(matrix[i] and not loop[i] for i in shared)
        l_only = sum(loop[i] and not matrix[i] for i in shared)
        neither = len(shared) - both - m_only - l_only
        body.append([model_name(card), str(len(shared)), str(both), str(m_only), str(l_only),
                     str(neither), f"{both + neither}/{len(shared)}" if shared else "–",
                     str(stable[card][1])])
    return header, body


FIGURES = (
    FigureSpec("4-4a_usage_setting", "Sycophancy under alternative usage",
               "BrokenMath [74, Sec. 4.3, Figs. 5-6]", usage_setting),
    FigureSpec("4-4b_loop_retention", "Survival without a flip, and correctness per turn",
               "SYCON-Bench [10]", loop_retention),
    FigureSpec("4-4c_turn_of_flip", "Distribution of Turn of Flip", "SYCON-Bench [10, Table 2]",
               turn_of_flip),
    FigureSpec("4-4d_flip_flop", "Answers that changed more than once",
               "SYCON-Bench [10]: Number of Flip", flip_flop),
)
TABLES = (
    TableSpec("4-4_loops", "Exploratory loops: Turn of Flip and Number of Flip", loop_table),
    TableSpec("4-4_concordance", "Single-turn against multi-turn on the same contradiction, "
              "item by item", concordance_table),
)

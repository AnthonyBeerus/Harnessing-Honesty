"""Section 4.2: can the harness repair it? The policies compared (H1).

What became of every correct first answer under each policy [15, Fig. 1;
74, Fig. 9], and the same as a flow from neutral to draft to final; how often
each policy repairs a conceded draft and how often it breaks a held one,
since self-correction can turn correct answers wrong [15], each in its own
population; which policies repair the same draft, since all three answer
one draft; among drafts the external report repaired, the share the
self-check also repaired; the override rate; and the planned contrasts [1,
Fig. 5]. The none final repeats only the answer request, so its repairs are
reversions on being asked again, not repair by a harness. Every interval
resamples items.
"""

from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from scripts.report.common import (
    INK,
    MUTED,
    POLICIES,
    POLICY_COLOUR,
    POLICY_LABEL,
    POLICY_TICK,
    SECONDARY,
    SINGLE,
    FigureSpec,
    ReportData,
    Rows,
    Table,
    TableSpec,
    VALID,
    draw_share,
    empty,
    finals,
    fraction,
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

# What became of a correct first answer. Cool colours end correct, warm ones
# end wrong; this order passes the adjacent colour-vision checks.
OUTCOMES = (
    ("held", "Held throughout", "#2a78d6", "white"),
    ("corrected", "Caved, then corrected", "#1baf7a", INK),
    ("flipped", "Held, then flipped", "#eda100", INK),
    ("stayed_wrong", "Caved, stayed wrong", "#e34948", "white"),
    ("draft_unknown", "Draft not a valid answer", "#8f8e88", "white"),
    ("final_missing", "Final not a valid answer", SECONDARY, INK),
)
CONTRAST_LABEL = {
    "h1_intrinsic": "H1 intrinsic − none",
    "h1_tool": "H1 external report − none",
    "h3": "H3 (intrinsic − none),\ndeductive − document",
}


def outcome(row: dict[str, str]) -> str | None:
    """What became of one cell's correct first answer; ``None`` if it was not correct."""
    if not is_true(row["initial_correct"]):
        return None
    final_known = row["final_state"] == VALID and known(row["final_correct"])
    if row["eligibility"] == "recovery" and final_known:
        return "corrected" if is_true(row["final_correct"]) else "stayed_wrong"
    if row["eligibility"] == "maintenance" and final_known:
        return "held" if is_true(row["final_correct"]) else "flipped"
    return "final_missing" if row["eligibility"] in ("recovery", "maintenance") else "draft_unknown"


def answer_change(data: ReportData, output: Path) -> list[Path]:
    """Stacked shares of what became of each correct first answer, per policy."""
    counts: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for row in data.rows:
        result = outcome(row)
        if result is not None:
            counts[row["card"]][row["policy"]][result] += 1
    cards = ordered(counts)
    figure, axes = panels(len(cards), height=3.4)
    for axis, card in zip(axes, cards):
        for x, policy in enumerate(POLICIES):
            tally = counts[card][policy]
            total = sum(tally.values())
            if not total:
                continue
            bottom = 0.0
            for key, _, colour, text in OUTCOMES:
                share = tally[key] / total
                if not share:
                    continue
                axis.bar(x, share, bottom=bottom, width=0.55, color=colour,
                         edgecolor="white", linewidth=1.5)
                if share >= 0.08:
                    axis.text(x, bottom + share / 2, f"{100 * share:.0f}%", ha="center",
                              va="center", fontsize=7.5, color=text)
                bottom += share
            label_bar(axis, x, 1.0, f"n={total}", 7.5)
        axis.set_title(model_name(card))
        axis.set_xticks(range(len(POLICIES)), [POLICY_TICK[p] for p in POLICIES], fontsize=8)
        axis.set_xlim(-0.6, len(POLICIES) - 0.4)
    axes[0].set_ylim(0, 1.1)
    axes[0].set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axes[0].set_ylabel("Share of cells with a\ncorrect first answer")
    handles = [Rectangle((0, 0), 1, 1, color=colour) for _, _, colour, _ in OUTCOMES]
    figure.legend(handles, [label for _, label, _, _ in OUTCOMES], loc="outside lower center",
                  ncols=len(OUTCOMES), fontsize=8)
    title(figure, "What became of a correct first answer under false pressure, by policy "
                  "(n: cells)")
    return save(figure, output, "4-2a_answer_change")


def _state(correct: str, state: str) -> str:
    if state != VALID or not known(correct):
        return "missing"
    return "correct" if is_true(correct) else "wrong"


STAGE_STATES = (("correct", "#2a78d6"), ("wrong", "#e34948"), ("missing", SECONDARY))


def flow(data: ReportData, output: Path) -> list[Path]:
    """Every cell from neutral answer to draft to final, per model and policy."""
    cards = ordered(row["card"] for row in data.rows)
    figure, grid = plt.subplots(len(cards), len(POLICIES), figsize=(9.6, 2.4 * len(cards)),
                                squeeze=False, layout="constrained")
    for r, card in enumerate(cards):
        for c, policy in enumerate(POLICIES):
            axis = grid[r][c]
            paths = [
                (_state(row["initial_correct"], row["initial_state"]),
                 _state(row["draft_correct"], row["draft_state"]),
                 _state(row["final_correct"], row["final_state"]))
                for row in data.rows if row["card"] == card and row["policy"] == policy
            ]
            _alluvial(axis, paths)
            if r == 0:
                axis.set_title(POLICY_LABEL[policy], fontsize=9)
            if c == 0:
                axis.set_ylabel(model_name(card), fontsize=9, color=INK)
    handles = [Rectangle((0, 0), 1, 1, color=colour) for _, colour in STAGE_STATES]
    figure.legend(handles, [s.capitalize() for s, _ in STAGE_STATES],
                  loc="outside lower center", ncols=3, fontsize=8)
    title(figure, "From neutral answer to draft to final, per model and policy")
    return save(figure, output, "4-2b_flow")


def _alluvial(axis, paths: list[tuple[str, str, str]]) -> None:
    """Three stacked columns joined by bands whose widths are the counts."""
    axis.grid(False)
    axis.set_xticks([0, 1, 2], ["Neutral", "Draft", "Final"], fontsize=7.5)
    axis.set_yticks([])
    for side in ("left", "bottom"):
        axis.spines[side].set_visible(False)
    total = len(paths)
    if not total:
        empty(axis, "no cells")
        return
    order = [state for state, _ in STAGE_STATES]
    colour = dict(STAGE_STATES)
    width = 0.12
    for stage in range(3):
        bottom = 0.0
        for state in order:
            share = sum(path[stage] == state for path in paths) / total
            if share:
                axis.bar(stage, share, bottom=bottom, width=width * 2, color=colour[state],
                         edgecolor="white", linewidth=1)
                if share >= 0.1:
                    axis.text(stage, bottom + share / 2, f"{round(share * total)}",
                              ha="center", va="center", fontsize=6.5,
                              color="white" if state != "missing" else INK)
            bottom += share
    for stage in range(2):
        source_top = {state: 0.0 for state in order}
        target_top = {state: 0.0 for state in order}
        source_base = _bases(paths, stage, order, total)
        target_base = _bases(paths, stage + 1, order, total)
        for a, b in product(order, order):
            share = sum(p[stage] == a and p[stage + 1] == b for p in paths) / total
            if not share:
                continue
            y0 = source_base[a] + source_top[a]
            y1 = target_base[b] + target_top[b]
            source_top[a] += share
            target_top[b] += share
            xs = np.linspace(stage + width, stage + 1 - width, 30)
            curve = (1 - np.cos(np.linspace(0, np.pi, 30))) / 2
            low = y0 + (y1 - y0) * curve
            axis.fill_between(xs, low, low + share, color=colour[b], alpha=0.35,
                              linewidth=0)
    axis.set_xlim(-0.3, 2.3)
    axis.set_ylim(0, 1.0)


def _bases(paths, stage: int, order: list[str], total: int) -> dict[str, float]:
    bases, bottom = {}, 0.0
    for state in order:
        bases[state] = bottom
        bottom += sum(path[stage] == state for path in paths) / total
    return bases


def repair_harm(rows: Rows) -> dict[str, dict[str, dict[str, list[tuple[str, bool]]]]]:
    """Per model and policy: repairs of conceded drafts, and harms to held ones."""
    found: dict[str, dict[str, dict[str, list[tuple[str, bool]]]]] = defaultdict(
        lambda: defaultdict(lambda: {"repair": [], "harm": []})
    )
    for row in rows:
        result = outcome(row)
        if result in ("corrected", "stayed_wrong"):
            found[row["card"]][row["policy"]]["repair"].append(
                (row["item_id"], result == "corrected"))
        elif result in ("held", "flipped"):
            found[row["card"]][row["policy"]]["harm"].append(
                (row["item_id"], result == "flipped"))
    return found


def repair_and_harm(data: ReportData, output: Path) -> list[Path]:
    """Repair rate of conceded drafts and harm rate of held drafts, per policy."""
    rates = repair_harm(data.rows)
    cards = ordered(rates)
    figure, grid = plt.subplots(2, len(cards), figsize=(3.2 * len(cards), 5.2), sharey=True,
                                squeeze=False, layout="constrained")
    for row, (kind, label) in enumerate((("repair", "Repair: conceded drafts\ncorrected"),
                                          ("harm", "Harm: held drafts\nflipped to wrong"))):
        for column, card in enumerate(cards):
            axis = grid[row][column]
            drawn = False
            for x, policy in enumerate(POLICIES):
                pairs = rates[card][policy][kind]
                if not pairs:
                    continue
                drawn = True
                draw_share(axis, x, share_interval(pairs), POLICY_COLOUR[policy])
            if not drawn:
                empty(axis, "No conceded drafts" if kind == "repair" else "No held drafts")
            axis.set_xticks(range(len(POLICIES)), [POLICY_TICK[p] for p in POLICIES],
                            fontsize=7.5)
            axis.set_xlim(-0.6, len(POLICIES) - 0.4)
            if row == 0:
                axis.set_title(model_name(card))
        grid[row][0].set_ylabel(label)
    share_axis(grid[0][0], 1.3)
    title(figure, "Repair of conceded drafts (recovery) and harm to held drafts "
                  "(maintenance), by policy, 95% intervals over items")
    return save(figure, output, "4-2c_repair_and_harm")


PATTERNS = [p for p in product((True, False), repeat=3)]


def repair_patterns(rows: Rows) -> dict[str, Counter]:
    """Per model: which policies corrected each conceded draft with three valid finals."""
    found: dict[str, Counter] = defaultdict(Counter)
    for card, by_branch in finals(rows).items():
        for by_policy in by_branch.values():
            cells = [by_policy[policy] for policy in POLICIES if policy in by_policy]
            if len(cells) != len(POLICIES):
                continue
            if any(c["eligibility"] != "recovery" or c["final_state"] != VALID
                   or not known(c["final_correct"]) for c in cells):
                continue
            found[card][tuple(is_true(c["final_correct"]) for c in cells)] += 1
    return found


def policy_patterns(data: ReportData, output: Path) -> list[Path]:
    """Which policies repaired each conceded draft: bars over a dot matrix."""
    patterns = repair_patterns(data.rows)
    cards = ordered(patterns)
    figure, grid = plt.subplots(2, len(cards), figsize=(3.4 * len(cards), 4.2),
                                height_ratios=(3, 1.2), squeeze=False, layout="constrained")
    for column, card in enumerate(cards):
        bars, dots = grid[0][column], grid[1][column]
        total = sum(patterns[card].values())
        for x, pattern in enumerate(PATTERNS):
            share = patterns[card][pattern] / total if total else 0
            bars.bar(x, share, width=0.6, color=SINGLE)
            if patterns[card][pattern]:
                label_bar(bars, x, share, str(patterns[card][pattern]), 7)
            for y, fixed in enumerate(pattern):
                dots.scatter(x, y, s=28, color=INK if fixed else SECONDARY, zorder=3)
        bars.set_title(f"{model_name(card)} (conceded drafts: {total})")
        bars.set_xticks([])
        share_axis(bars, 1.15)
        dots.set_yticks(range(3), [POLICY_LABEL[p] for p in POLICIES], fontsize=7)
        dots.set_xticks([])
        dots.set_ylim(2.6, -0.6)
        dots.grid(False)
        for side in ("left", "bottom"):
            dots.spines[side].set_visible(False)
    grid[0][0].set_ylabel("Share of conceded drafts")
    title(figure, "Which policies corrected the same conceded draft (dark dot: corrected)")
    return save(figure, output, "4-2d_policy_patterns")


def within_ceiling_units(rows: Rows) -> dict[str, list[tuple[str, bool]]]:
    """Per model: (item, intrinsic also repaired) for each conceded draft the report repaired.

    Paired on the shared draft, so both arms answer the same conceded branch.
    """
    found: dict[str, list[tuple[str, bool]]] = defaultdict(list)
    for card, by_branch in finals(rows).items():
        for (item, _), by_policy in by_branch.items():
            cells = [by_policy[policy] for policy in ("intrinsic", "tool") if policy in by_policy]
            if len(cells) != 2 or any(
                    c["eligibility"] != "recovery" or c["final_state"] != VALID
                    or not known(c["final_correct"]) for c in cells):
                continue
            intrinsic, tool = (is_true(c["final_correct"]) for c in cells)
            if tool:
                found[card].append((item, intrinsic))
    return found


def within_ceiling(data: ReportData, output: Path) -> list[Path]:
    """Among conceded drafts the external report repaired, the share the self-check also repaired."""
    units = within_ceiling_units(data.rows)
    cards = ordered(row["card"] for row in data.rows)
    figure, axis = plt.subplots(figsize=(1.4 * len(cards) + 1.6, 3.2), layout="constrained")
    for x, card in enumerate(cards):
        if not units.get(card):
            label_bar(axis, x, 0, "no drafts the\nreport repaired")
            continue
        draw_share(axis, x, share_interval(units[card]), POLICY_COLOUR["intrinsic"], 0.5, 8)
    axis.set_xticks(range(len(cards)), [model_name(card) for card in cards])
    share_axis(axis, 1.35)
    axis.set_ylabel("Also repaired by the self-check\n(per conceded branch)")
    title(figure, "Report-repaired drafts the self-check also repaired,\n"
                  "95% intervals over items")
    return save(figure, output, "4-2e_within_ceiling")


def override(data: ReportData, output: Path) -> list[Path]:
    """Finals that disagree with the external report, per model and population."""
    cards = ordered(data.results["reports"])
    figure, axis = plt.subplots(figsize=(1.6 * len(cards) + 2.0, 3.0), layout="constrained")
    counts = repair_harm(data.rows)
    for x, card in enumerate(cards):
        rates = data.results["reports"][card].get("override") or {}
        for k, population in enumerate(("recovery", "maintenance")):
            value = rates.get(population)
            position = x - 0.2 + 0.4 * k
            kind = "repair" if population == "recovery" else "harm"
            pairs = counts[card]["tool"][kind]
            wrong = (len(pairs) - sum(h for _, h in pairs)) if kind == "repair" else sum(
                h for _, h in pairs)
            if value is None:
                continue
            axis.bar(position, value, width=0.36, color=("#86b6ef", "#256abf")[k],
                     label=population.capitalize() if x == 0 else None)
            label_bar(axis, position, value, f"{wrong}/{len(pairs)}", 7)
    axis.set_xticks(range(len(cards)), [model_name(card) for card in cards])
    share_axis(axis, 1.2)
    axis.set_ylabel("External-report finals that\ndisagree with the report (per cell)")
    figure.legend(loc="outside lower center", ncols=2, fontsize=8)
    title(figure, "Override: finals against the labelled external report (ideal 0)")
    return save(figure, output, "4-2f_override")


def contrasts(data: ReportData, output: Path) -> list[Path]:
    """The planned contrasts with 95% intervals."""
    results = data.results
    cards = ordered(results["reports"])
    figure, axes = panels(len(cards), height=2.6)
    order = list(CONTRAST_LABEL)
    for axis, card in zip(axes, cards):
        found = {c["contrast"]: c for c in results["reports"][card]["primary"]["contrasts"]}
        axis.axvline(0, color=MUTED, linewidth=0.8)
        for y, name in enumerate(order):
            contrast = found.get(name)
            if contrast is None or contrast["estimate"] is None:
                continue
            axis.hlines(y, contrast["ci_low"], contrast["ci_high"], color=INK, linewidth=2)
            axis.plot(contrast["estimate"], y, "o", markersize=7, color=SINGLE,
                      markeredgecolor="white", markeredgewidth=1.5)
        axis.set_yticks(range(len(order)), [CONTRAST_LABEL[c] for c in order])
        axis.invert_yaxis()
        axis.set_xlim(-1.05, 1.05)
        axis.grid(axis="x")
        axis.grid(axis="y", visible=False)
        axis.set_title(model_name(card))
        axis.set_xlabel("Difference in regressive-shift rate\n(negative: fewer finals wrong)")
    gate = ("all estimation-only under the power gate" if not results.get("confirmatory")
            else "Holm-adjusted")
    title(figure, f"Planned contrasts, recovery population, 95% scenario-bootstrap "
                  f"intervals ({gate})")
    return save(figure, output, "4-2g_contrasts")


def shift_table(data: ReportData) -> Table:
    """Regressive-shift rate per model, population and policy, with its scenarios."""
    header = ["Model", "Population", "Policy", "Shifted / valid finals", "Missing finals",
              "Missing as no shift", "Missing as shift"]
    body = []
    for card in ordered(data.results["reports"]):
        for s in data.results["reports"][card]["summaries"]:
            body.append([model_name(card), s["population"], POLICY_LABEL[s["policy"]],
                         fraction(s["n_shift"], s["n_valid"]), str(s["n_missing_final"]),
                         number(s["lower_bound"]), number(s["upper_bound"])])
    return header, body


def repair_table(data: ReportData) -> Table:
    header = ["Model", "Policy", "Repaired / conceded (recovery)", "Broken / held (maintenance)"]
    rates = repair_harm(data.rows)
    body = []
    for card in ordered(rates):
        for policy in POLICIES:
            repair, harm = rates[card][policy]["repair"], rates[card][policy]["harm"]
            body.append([model_name(card), POLICY_LABEL[policy],
                         fraction(sum(h for _, h in repair), len(repair)),
                         fraction(sum(h for _, h in harm), len(harm))])
    return header, body


def contrast_table(data: ReportData) -> Table:
    header = ["Model", "Contrast", "Estimate", "95% interval", "Holm p", "Failed resamples",
              "Status"]
    body = []
    for card in ordered(data.results["reports"]):
        for c in data.results["reports"][card]["primary"]["contrasts"]:
            status = ("confirmed" if c["confirmed"] else
                      "not confirmed" if c["confirmatory"] else "estimation-only")
            interval = ("–" if c["ci_low"] is None else
                        f"[{c['ci_low']:+.3f}, {c['ci_high']:+.3f}]")
            body.append([model_name(card), CONTRAST_LABEL[c["contrast"]].replace("\n", " "),
                         "–" if c["estimate"] is None else f"{c['estimate']:+.3f}", interval,
                         number(c["p_holm"], 4), str(c["failed_resamples"]), status])
    return header, body


FIGURES = (
    FigureSpec("4-2a_answer_change", "What became of a correct first answer, by policy",
               "Huang et al. [15, Fig. 1]; BrokenMath [74, Fig. 9]", answer_change),
    FigureSpec("4-2b_flow", "Neutral answer to draft to final, per model and policy",
               "answer-change flow", flow),
    FigureSpec("4-2c_repair_and_harm", "Repair of conceded drafts and harm to held drafts",
               "Huang et al. [15]: correct to incorrect after self-correction", repair_and_harm),
    FigureSpec("4-2d_policy_patterns", "Which policies corrected the same conceded draft",
               "paired design", policy_patterns),
    FigureSpec("4-2e_within_ceiling", "Report-repaired drafts the self-check also repaired",
               "Kamoi et al. [16]: external feedback", within_ceiling),
    FigureSpec("4-2f_override", "Override of the external report", "registered process measure",
               override),
    FigureSpec("4-2g_contrasts", "Planned contrasts with 95% intervals",
               "Sharma et al. [1, Fig. 5]", contrasts),
)
TABLES = (
    TableSpec("4-2_shift", "Regressive shift by policy, with the missing-final scenarios",
              shift_table),
    TableSpec("4-2_repair", "Repair and harm by policy, each in its own population",
              repair_table),
    TableSpec("4-2_contrasts", "Planned contrasts, recovery population", contrast_table),
)

"""Section 4.5: how far the results can be trusted.

The sensitivity analyses beside the primary contrasts, missing answers by
policy (a policy that makes a model drop the format would make missingness
differ between arms), the secondary odds ratios, the bootstrap distributions
behind each interval, and, across repeated runs, answer agreement [10,
Table 6], whether the estimates move, and the share of cells answered
correctly in every run (pass^k) or in at least one (pass@k) [41, "How to
think about non-determinism in evaluations for agents"].
"""

import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from scripts.report.common import (
    INK,
    MUTED,
    POLICIES,
    PRESSURES,
    RAMP,
    SECONDARY,
    SINGLE,
    FigureSpec,
    ReportData,
    Table,
    TableSpec,
    VALID,
    attempts,
    collection_events,
    fraction,
    is_true,
    label_bar,
    model_name,
    ordered,
    panels,
    save,
    share_axis,
    title,
)
from scripts.report.repair import CONTRAST_LABEL

SHORT = {"h1_intrinsic": "H1 intrinsic", "h1_tool": "H1 report", "h3": "H3"}


def sensitivity(data: ReportData, output: Path) -> list[Path]:
    """Each contrast under the primary analysis and every sensitivity analysis."""
    cards = ordered(data.results["reports"])
    first = data.results["reports"][cards[0]]
    scenarios = ["primary", *(s["label"] for s in first["sensitivity"])]
    rows = [(c, s) for c in CONTRAST_LABEL for s in scenarios]
    figure, axes = panels(len(cards), height=0.32 * len(rows) + 1.2, width=3.4)
    for axis, card in zip(axes, cards):
        report = data.results["reports"][card]
        results = {"primary": report["primary"]}
        results.update({s["label"]: s["result"] for s in report["sensitivity"]})
        axis.axvline(0, color=MUTED, linewidth=0.8)
        for y, (contrast, scenario) in enumerate(rows):
            found = {c["contrast"]: c for c in results.get(scenario, {}).get("contrasts", [])}
            c = found.get(contrast)
            if c is None or c["estimate"] is None:
                axis.text(0, y, "no estimate", ha="center", va="center", fontsize=6.5,
                          color=MUTED)
                continue
            colour = SINGLE if scenario == "primary" else MUTED
            axis.hlines(y, c["ci_low"], c["ci_high"], color=colour, linewidth=2)
            axis.plot(c["estimate"], y, "o", markersize=6, color=colour,
                      markeredgecolor="white", markeredgewidth=1.2)
        axis.set_yticks(range(len(rows)), [f"{SHORT[c]} · {s}" for c, s in rows], fontsize=7)
        axis.set_ylim(len(rows) - 0.5, -0.5)
        axis.set_xlim(-1.05, 1.05)
        axis.grid(axis="x")
        axis.grid(axis="y", visible=False)
        axis.set_title(model_name(card))
        axis.set_xlabel("Difference in regressive-shift rate")
    title(figure, "Sensitivity: each contrast under the primary analysis (blue) and every "
                  "sensitivity analysis (grey), 95% intervals")
    return save(figure, output, "4-5a_sensitivity")


def missingness_counts(data: ReportData) -> dict[str, dict[str, list[int]]]:
    """Per model: [not valid, total] for each call group, each in its own unit."""
    counts: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    neutral: dict[tuple[str, str], str] = {}
    drafts: dict[tuple[str, str, str], str] = {}
    for row in data.rows:
        neutral[(row["card"], row["item_id"])] = row["initial_state"]
        if row["initial_state"] == VALID:
            drafts[(row["card"], row["item_id"], row["pressure"])] = row["draft_state"]
        if row["draft_state"] == VALID:
            cell = counts[row["card"]][f"Final: {row['policy']}"]
            cell[0] += row["final_state"] != VALID
            cell[1] += 1
    for (card, _), state in neutral.items():
        counts[card]["Neutral"][0] += state != VALID
        counts[card]["Neutral"][1] += 1
    for (card, _, _), state in drafts.items():
        counts[card]["Draft"][0] += state != VALID
        counts[card]["Draft"][1] += 1
    loop_neutral: dict[tuple[str, str], str] = {}
    for row in data.loops:
        loop_neutral[(row["card"], row["item_id"])] = row["initial_state"]
        if row["initial_state"] != VALID:
            continue
        states = [row[f"turn{t}_state"] for t in (1, 2, 3)]
        cell = counts[row["card"]][f"Loop: {row['policy']}"]
        cell[0] += any(state and state != VALID for state in states)
        cell[1] += 1
    for (card, _), state in loop_neutral.items():
        counts[card]["Loop: neutral"][0] += state != VALID
        counts[card]["Loop: neutral"][1] += 1
    return counts


GROUPS = (
    ("Neutral", "item"), ("Draft", "branch"),
    *((f"Final: {p}", "cell") for p in POLICIES),
    ("Loop: neutral", "item"),
    *((f"Loop: {p}", "loop") for p in POLICIES),
)


def missingness(data: ReportData, output: Path) -> list[Path]:
    """Answers that were not a valid yes or no, by call group and policy."""
    counts = missingness_counts(data)
    cards = ordered(counts)
    figure, axes = panels(len(cards), height=3.2, width=4.2)
    for axis, card in zip(axes, cards):
        for x, (group, _) in enumerate(GROUPS):
            k, n = counts[card][group]
            if not n:
                continue
            axis.bar(x, k / n, width=0.6, color=SINGLE if group.startswith(("Final", "Loop"))
                     else SECONDARY)
            label_bar(axis, x, k / n, f"{k}/{n}", 6.5)
        axis.set_title(model_name(card))
        axis.set_xticks(range(len(GROUPS)),
                        [f"{g.replace(': ', chr(10))}{chr(10)}({unit})" for g, unit in GROUPS],
                        fontsize=5.5)
    top = max((k / n for c in counts.values() for k, n in c.values() if n), default=0)
    axes[0].set_ylim(0, max(0.1, top * 1.4))
    axes[0].set_ylabel("Share not a valid yes or no\n(after retries; unit in brackets;\na loop counts if any turn is)")
    title(figure, "Missing answers by call group and policy: does a policy break the format?")
    return save(figure, output, "4-5b_missingness")


def odds_ratios(data: ReportData, output: Path) -> list[Path]:
    """The secondary mixed-logit odds ratios, or why a fit gave none."""
    cards = ordered(data.results["reports"])
    rows = [(t, s) for t in ("intrinsic", "tool") for s in ("document_grounded", "deductive")]
    figure, axes = panels(len(cards), height=2.4, width=3.3)
    for axis, card in zip(axes, cards):
        odds = {o["treatment"]: o for o in data.results["reports"][card]["odds"]}
        axis.axvline(1, color=MUTED, linewidth=0.8)
        for y, (treatment, stratum) in enumerate(rows):
            entry = odds.get(treatment)
            value = entry.get(stratum) if entry else None
            if value is None or value <= 0:
                status = entry["fit"]["status"] if entry else "absent"
                axis.text(1, y, f"no estimate ({status})", ha="center", va="center",
                          fontsize=7, color=MUTED)
                continue
            axis.plot(value, y, "o", markersize=7, color=SINGLE, markeredgecolor="white")
            axis.annotate(f"{value:.2f}", (value, y), xytext=(6, 0), textcoords="offset points",
                          va="center", fontsize=7, color=INK)
        axis.set_xscale("log")
        axis.set_xlim(0.01, 100)
        axis.set_yticks(range(len(rows)),
                        [f"{t} vs none · {s.replace('_', '-')}" for t, s in rows], fontsize=7)
        axis.set_ylim(len(rows) - 0.5, -0.5)
        axis.grid(axis="x")
        axis.grid(axis="y", visible=False)
        axis.set_title(model_name(card))
        axis.set_xlabel("Odds ratio of regressive shift (log scale)")
    title(figure, "Secondary: mixed-logit odds ratios against none, recovery population "
                  "(points only; no decision depends on them)")
    return save(figure, output, "4-5c_odds_ratios")


def replay_draws(data: ReportData) -> dict[str, dict[str, list[float]]]:
    """The primary bootstrap's resampled estimates, replayed and checked.

    The analysis keeps only the interval and p-value, so the same resampler is
    run again with the recorded seed and count. A replay whose interval or
    p-value differs from the reported one is refused, so a drawn distribution
    is the one the reported numbers came from.
    """
    from harnessing_honesty.analysis.bootstrap import (
        ScenarioResampler,
        percentile_interval,
        percentile_p_value,
        planned_estimates,
    )
    from harnessing_honesty.analysis.collected import item_families
    from harnessing_honesty.domain.enums import Eligibility, Track
    from harnessing_honesty.evaluation.collection import load_collection

    from scripts.compare_runs import collection_rows
    from scripts.development_results import development_items

    assert data.collection is not None
    spec, _ = load_collection(data.collection)
    families = dict(item_families())
    if spec.track is Track.DEV:
        families.update(development_items()[1])
    _, rows = collection_rows(data.collection)
    replayed: dict[str, dict[str, list[float]]] = {}
    for card, (matrix, _) in rows.items():
        primary = data.results["reports"][card]["primary"]
        rng = np.random.default_rng(primary["seed"])
        resampler = ScenarioResampler(matrix, families)
        draws: dict[str, list[float]] = defaultdict(list)
        for _ in range(primary["n_resamples"]):
            sample = resampler.draw(rng)
            for contrast, value in planned_estimates(sample, Eligibility.RECOVERY).items():
                if value is not None:
                    draws[contrast.value].append(value)
        for reported in primary["contrasts"]:
            values = draws.get(reported["contrast"], [])
            if not values or reported["ci_low"] is None:
                continue
            low, high = percentile_interval(values)
            same = (math.isclose(low, reported["ci_low"]) and math.isclose(high, reported["ci_high"])
                    and math.isclose(percentile_p_value(values), reported["p_value"]))
            if not same:
                raise ValueError(f"{card} {reported['contrast']}: the replayed bootstrap "
                                 "does not reproduce the reported interval")
        replayed[card] = dict(draws)
    return replayed


def bootstrap_distributions(data: ReportData, output: Path) -> list[Path] | None:
    """Resampled estimates behind each interval, per model and contrast."""
    if data.collection is None:
        return None
    replayed = replay_draws(data)
    cards = ordered(replayed)
    figure, grid = plt.subplots(len(cards), len(CONTRAST_LABEL), figsize=(9.6, 2.2 * len(cards)),
                                squeeze=False, layout="constrained")
    for r, card in enumerate(cards):
        found = {c["contrast"]: c for c in data.results["reports"][card]["primary"]["contrasts"]}
        for c, contrast in enumerate(CONTRAST_LABEL):
            axis = grid[r][c]
            values = replayed[card].get(contrast, [])
            reported = found.get(contrast)
            if values:
                bins = np.linspace(-1, 1, 41)
                axis.hist(values, bins=bins, color=RAMP[2], edgecolor="white", linewidth=0.5)
                if reported and reported["ci_low"] is not None:
                    axis.axvspan(reported["ci_low"], reported["ci_high"], color=RAMP[0],
                                 zorder=0)
                    axis.axvline(reported["estimate"], color=INK, linewidth=1.2)
            axis.axvline(0, color=MUTED, linewidth=0.8, linestyle="-")
            axis.set_xlim(-1.05, 1.05)
            axis.set_yticks([])
            if r == 0:
                axis.set_title(CONTRAST_LABEL[contrast].replace("\n", " "), fontsize=8.5)
            if c == 0:
                axis.set_ylabel(model_name(card), fontsize=9, color=INK)
    title(figure, "Bootstrap distributions behind each interval (shaded: 95% interval; "
                  "dark line: estimate)")
    return save(figure, output, "4-5d_bootstrap")


def _agreement(comparison: dict) -> dict[str, dict[str, list[int]]]:
    totals: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for row in comparison["agreement"]:
        group = "Loop calls" if row["stage"].startswith("loop") else "Matrix calls"
        cell = totals[row["card"]][group]
        cell[0] += row["agree"]
        cell[1] += row["agree"] + row["disagree"]
    return totals


def stability(data: ReportData, output: Path) -> list[Path] | None:
    """Identical requests answered identically across repeated runs."""
    if data.comparison is None:
        return None
    totals = _agreement(data.comparison)
    cards = ordered(totals)
    figure, axes = panels(len(cards), height=2.6)
    for axis, card in zip(axes, cards):
        for x, group in enumerate(("Matrix calls", "Loop calls")):
            k, n = totals[card][group]
            if not n:
                continue
            axis.bar(x, k / n, width=0.5, color=SINGLE)
            label_bar(axis, x, k / n, f"{100 * k / n:.1f}%\n{k}/{n}", 8)
        axis.set_title(model_name(card))
        axis.set_xticks(range(2), ["Matrix calls", "Loop calls"])
    share_axis(axes[0], 1.25)
    axes[0].set_ylabel("Identical requests,\nidentical answer")
    title(figure, f"Answer agreement at temperature 0 across {data.comparison['pairs']} "
                  "pairs of runs, among calls whose requests were identical")
    return save(figure, output, "4-5e_answer_agreement")


def stability_table(data: ReportData) -> Table | None:
    if data.comparison is None:
        return None
    totals = _agreement(data.comparison)
    diverged: dict[str, int] = defaultdict(int)
    for row in data.comparison["agreement"]:
        diverged[row["card"]] += row["diverged_earlier"]
    header = ["Model", "Matrix calls agreeing", "Loop calls agreeing",
              "Not compared: an earlier answer differed", "Pairs of runs"]
    return header, [[model_name(card), fraction(*totals[card]["Matrix calls"]),
                     fraction(*totals[card]["Loop calls"]), str(diverged[card]),
                     str(data.comparison["pairs"])]
                    for card in ordered(totals)]


def _runs(data: ReportData) -> list[tuple[str, dict, list]]:
    return [("this run", data.results, data.rows), *data.replicates]


def estimate_stability(data: ReportData, output: Path) -> list[Path] | None:
    """Each contrast's estimate and interval in every run, side by side."""
    if not data.replicates:
        return None
    runs = _runs(data)
    cards = ordered(data.results["reports"])
    figure, axes = panels(len(cards), height=2.9)
    step = 0.6 / max(len(runs) - 1, 1)
    for axis, card in zip(axes, cards):
        axis.axvline(0, color=MUTED, linewidth=0.8)
        for r, (name, results, _) in enumerate(runs):
            report = results["reports"].get(card)
            if report is None:
                continue
            found = {c["contrast"]: c for c in report["primary"]["contrasts"]}
            colour = SINGLE if r == 0 else MUTED
            for y, contrast in enumerate(CONTRAST_LABEL):
                c = found.get(contrast)
                if c is None or c["estimate"] is None:
                    continue
                position = y - 0.3 + step * r
                axis.hlines(position, c["ci_low"], c["ci_high"], color=colour, linewidth=1.5)
                axis.plot(c["estimate"], position, "o", markersize=5, color=colour,
                          markeredgecolor="white")
        axis.set_yticks(range(len(CONTRAST_LABEL)), list(CONTRAST_LABEL.values()), fontsize=7.5)
        axis.set_ylim(len(CONTRAST_LABEL) - 0.5, -0.5)
        axis.set_xlim(-1.05, 1.05)
        axis.grid(axis="x")
        axis.grid(axis="y", visible=False)
        axis.set_title(model_name(card))
    title(figure, f"Do the estimates move between runs? This run (blue) and "
                  f"{len(runs) - 1} repeat(s) (grey), 95% intervals")
    return save(figure, output, "4-5f_estimate_stability")


def consistency(data: ReportData) -> dict[str, tuple[float, float, float, int, int]]:
    """Per model: pass@1, pass^k, pass@k over final cells present in every run, and k, n."""
    runs = _runs(data)
    correct: dict[str, dict[tuple[str, str, str], list[bool]]] = defaultdict(
        lambda: defaultdict(list))
    for _, _, rows in runs:
        for row in rows:
            correct[row["card"]][(row["item_id"], row["pressure"], row["policy"])].append(
                row["final_state"] == VALID and is_true(row["final_correct"]))
    k = len(runs)
    found = {}
    for card in ordered(correct):
        cells = [hits for hits in correct[card].values() if len(hits) == k]
        if not cells:
            continue
        n = len(cells)
        found[card] = (sum(h[0] for h in cells) / n, sum(all(h) for h in cells) / n,
                       sum(any(h) for h in cells) / n, k, n)
    return found


def pass_k(data: ReportData, output: Path) -> list[Path] | None:
    """Finals correct in the first run, in every run (pass^k) and in any run (pass@k)."""
    if not data.replicates:
        return None
    found = consistency(data)
    cards = list(found)
    labels = (("pass@1 (this run)", RAMP[2]), ("pass^k (every run)", RAMP[4]),
              ("pass@k (any run)", RAMP[1]))
    figure, axis = plt.subplots(figsize=(1.9 * len(cards) + 1.8, 3.2), layout="constrained")
    for x, card in enumerate(cards):
        values = found[card][:3]
        for s, ((label, colour), value) in enumerate(zip(labels, values)):
            position = x - 0.27 + 0.27 * s
            axis.bar(position, value, width=0.24, color=colour, label=label if x == 0 else None)
            label_bar(axis, position, value, f"{100 * value:.0f}%", 7)
    k, n = next(iter(found.values()))[3:] if found else (0, 0)
    axis.set_xticks(range(len(cards)), [model_name(card) for card in cards])
    share_axis(axis, 1.15)
    axis.set_ylabel("Final cells answered correctly")
    figure.legend(loc="outside lower center", ncols=3, fontsize=8)
    title(figure, f"Consistency across k = {k} runs ({n} final cells per model)")
    return save(figure, output, "4-5g_pass_k")


def retries_table(data: ReportData) -> Table | None:
    """Attempts, retries and failures per model, from the recorded events."""
    if data.collection is None:
        return None
    header = ["Model", "Calls", "Attempts", "Retries", "Parse failures", "Provider failures",
              "Protocol failures", "Interrupted"]
    body = []
    for card, events in ((c, e) for c, e in collection_events(data.collection).items()):
        found = attempts(events)
        outcomes = Counter(a["outcome"] for a in found)
        calls = len({a["call_id"] for a in found})
        body.append([model_name(card), str(calls), str(len(found)),
                     str(sum(a["attempt"] > 1 for a in found)), str(outcomes["parse"]),
                     str(outcomes["provider"]), str(outcomes["protocol"]),
                     str(outcomes["attempt_interrupted"])])
    rank = {model_name(card): i for i, card in enumerate(ordered(
        collection_events(data.collection)))}
    body.sort(key=lambda line: rank[line[0]])
    return header, body


def redraw_table(data: ReportData) -> Table:
    """The matrix and loop neutral calls send the same request: how often the two draws agree."""
    pairs: dict[str, list[tuple[str, str]]] = defaultdict(list)
    loop = {(r["card"], r["item_id"]): r["initial_correct"] for r in data.loops}
    seen: set[tuple[str, str]] = set()
    for row in data.rows:
        key = (row["card"], row["item_id"])
        if key in seen or key not in loop:
            continue
        seen.add(key)
        pairs[row["card"]].append((row["initial_correct"], loop[key]))
    header = ["Model", "Items with both draws known", "Draws agree", "Matrix correct, loop wrong",
              "Matrix wrong, loop correct"]
    body = []
    for card in ordered(pairs):
        both = [(m, lo) for m, lo in pairs[card] if m in ("True", "False") and lo in ("True", "False")]
        body.append([model_name(card), str(len(both)), fraction(sum(m == lo for m, lo in both),
                                                                len(both)),
                     str(sum(m == "True" and lo == "False" for m, lo in both)),
                     str(sum(m == "False" and lo == "True" for m, lo in both))])
    return header, body


ANSWER_AT_END = re.compile(r"\b(yes|no)\W*$", re.IGNORECASE)


def invalid_with_answer_table(data: ReportData) -> Table:
    """Responses that were not exactly yes or no, but end in one: disclosed, never rescored."""
    found: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    seen: set[tuple] = set()
    for row in data.rows:
        for stage, state, raw, key in (
                ("draft", row["draft_state"], row["draft_raw_response"],
                 (row["card"], row["item_id"], row["pressure"])),
                ("final", row["final_state"], row["final_raw_response"],
                 (row["card"], row["item_id"], row["pressure"], row["policy"]))):
            if state == "invalid" and (stage, key) not in seen:
                seen.add((stage, key))
                found[row["card"]][1] += 1
                found[row["card"]][0] += bool(ANSWER_AT_END.search(raw or ""))
    for row in data.loops:
        for t in (1, 2, 3):
            if row[f"turn{t}_state"] == "invalid":
                found[row["card"]][1] += 1
                found[row["card"]][0] += bool(ANSWER_AT_END.search(row[f"turn{t}_raw_response"]
                                                                   or ""))
    header = ["Model", "Invalid responses", "Ending in yes or no (not rescored)"]
    return header, [[model_name(card), str(found[card][1]), str(found[card][0])]
                    for card in ordered(row["card"] for row in data.rows)]


def balance_table(data: ReportData) -> Table:
    """Mean dispatch position by policy and by pressure: an audit of the randomised order."""
    finals: dict[tuple[str, str], list[int]] = defaultdict(list)
    drafts: dict[tuple[str, str], list[int]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    for row in data.rows:
        if row["final_position"]:
            finals[(row["card"], row["policy"])].append(int(row["final_position"]))
        key = (row["card"], row["item_id"], row["pressure"])
        if row["draft_position"] and key not in seen:
            seen.add(key)
            drafts[(row["card"], row["pressure"])].append(int(row["draft_position"]))
    header = ["Model", "Mean final position (1-9): none / intrinsic / tool",
              "Mean draft position (1-3): contradiction / authority / citation"]

    def mean(values: list[int]) -> str:
        return f"{sum(values) / len(values):.2f}" if values else "–"

    return header, [[model_name(card),
                     " / ".join(mean(finals[(card, p)]) for p in POLICIES),
                     " / ".join(mean(drafts[(card, p)]) for p in PRESSURES)]
                    for card in ordered(row["card"] for row in data.rows)]


FIGURES = (
    FigureSpec("4-5a_sensitivity", "Contrasts under every sensitivity analysis",
               "registered sensitivity analyses", sensitivity),
    FigureSpec("4-5b_missingness", "Missing answers by call group and policy",
               "differential missingness", missingness),
    FigureSpec("4-5c_odds_ratios", "Secondary mixed-logit odds ratios",
               "proposal's secondary analysis", odds_ratios),
    FigureSpec("4-5d_bootstrap", "Bootstrap distributions behind each interval",
               "scenario bootstrap", bootstrap_distributions, needs="--collection"),
    FigureSpec("4-5e_answer_agreement", "Answer agreement between repeated runs",
               "SYCON-Bench [10, Table 6]", stability, needs="--stability"),
    FigureSpec("4-5f_estimate_stability", "Estimates across repeated runs",
               "repeated runs", estimate_stability, needs="--replicate"),
    FigureSpec("4-5g_pass_k", "pass@1, pass^k and pass@k across runs",
               "Anthropic [41]: non-determinism", pass_k, needs="--replicate"),
)
TABLES = (
    TableSpec("4-5_agreement", "Answer agreement between repeated runs", stability_table,
              needs="--stability"),
    TableSpec("4-5_retries", "Attempts, retries and failures", retries_table,
              needs="--collection"),
    TableSpec("4-5_redraw", "Neutral re-draw: the matrix and loop neutral answers to the same "
              "request", redraw_table),
    TableSpec("4-5_invalid_with_answer", "Invalid responses that end in yes or no "
              "(disclosure; never rescored)", invalid_with_answer_table),
    TableSpec("4-5_balance", "Dispatch-position balance (audit of the randomised order)",
              balance_table),
)

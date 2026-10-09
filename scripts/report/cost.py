"""Section 4.6: what does each harness cost?

Calls are matched across policies, so the policies cost the same number of
calls, but not the same tokens: the external report adds input. Costs come
from the provider's recorded usage, every attempt included. The cost of an
additional repair compares each policy with the re-ask control on the same
conceded drafts: its extra final-call credits divided by the extra drafts it
corrected, with an interval from resampling items. Shared neutral and draft
calls cost every policy the same and are left out.
"""

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

from scripts.report.common import (
    POLICIES,
    POLICY_COLOUR,
    POLICY_TICK,
    FigureSpec,
    ReportData,
    Table,
    TableSpec,
    attempts,
    collection_events,
    label_bar,
    model_name,
    ordered,
    panels,
    save,
    title,
)


def usage(data: ReportData) -> dict[str, dict[str, dict[str, float]]]:
    """Per model and component: attempts, calls, input and output tokens and cost."""
    assert data.collection is not None
    found: dict[str, dict[str, dict[str, float]]] = {}
    for card, events in collection_events(data.collection).items():
        totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        calls: dict[str, set] = defaultdict(set)
        for attempt in attempts(events):
            cell = totals[attempt["component"]]
            cell["attempts"] += 1
            cell["input_tokens"] += attempt["input_tokens"]
            cell["output_tokens"] += attempt["output_tokens"]
            cell["cost"] += attempt["cost"]
            calls[attempt["component"]].add(attempt["call_id"])
        for name, ids in calls.items():
            totals[name]["calls"] = len(ids)
        found[card] = totals
    return found


def tokens_and_cost(data: ReportData, output: Path) -> list[Path] | None:
    """Mean input tokens and cost per final call, by policy and model."""
    if data.collection is None:
        return None
    found = usage(data)
    cards = ordered(found)
    figure, grid = plt.subplots(2, len(cards), figsize=(3.2 * len(cards), 5.4), squeeze=False,
                                layout="constrained")
    # Credits per final call are tiny, so they are shown per 1,000 final calls.
    measures = (("input_tokens", 1, "Input tokens\nper final call", "{:.0f}"),
                ("cost", 1000, "Credits per\n1,000 final calls", "{:.3g}"))
    for row, (field, scale, label, fmt) in enumerate(measures):
        for column, card in enumerate(cards):
            axis = grid[row][column]
            for x, policy in enumerate(POLICIES):
                cell = found[card].get(f"Final: {policy}")
                if not cell or not cell["calls"]:
                    continue
                value = scale * cell[field] / cell["calls"]
                axis.bar(x, value, width=0.5, color=POLICY_COLOUR[policy])
                label_bar(axis, x, value, fmt.format(value), 7)
            if row == 0:
                axis.set_title(model_name(card))
            axis.set_xticks(range(len(POLICIES)), [POLICY_TICK[p] for p in POLICIES],
                            fontsize=7.5)
            axis.margins(y=0.15)
        grid[row][0].set_ylabel(label)
    title(figure, "Harness cost: tokens and credits per final call, by policy "
                  "(all attempts included)")
    return save(figure, output, "4-6a_tokens_and_cost")


def final_credits(data: ReportData) -> dict[str, dict[tuple[str, str, str], float]]:
    """Per model: credits of each final call, by (item, pressure, policy), all attempts."""
    assert data.collection is not None
    found: dict[str, dict[tuple[str, str, str], float]] = {}
    for card, events in collection_events(data.collection).items():
        calls: dict[str, tuple[str, str, str]] = {}
        credits: dict[tuple[str, str, str], float] = defaultdict(float)
        for event in events:
            call = event.get("call_id")
            if call is None:
                continue
            if event["kind"] == "request_sent" and event.get("stage") == "pressured_final":
                pressure, policy = str(event.get("cell_identity")).split("__")
                calls[call] = (str(event.get("scenario_id")), pressure, policy)
            elif call in calls and event["kind"] in ("response_received", "request_failed"):
                credits[calls[call]] += (event.get("usage") or {}).get("cost") or 0.0
        found[card] = credits
    return found


def incremental_units(data: ReportData) -> dict[str, dict[str, list[tuple[str, float, int]]]]:
    """Per model and policy: (item, extra credits, extra repairs) for each conceded draft.

    Both the policy's final and the re-ask control's final are valid answers to
    the same conceded draft, so the difference is paired.
    """
    credits = final_credits(data)
    finals: dict[tuple[str, str, str, str], dict[str, str]] = {
        (r["card"], r["item_id"], r["pressure"], r["policy"]): r for r in data.rows}
    found: dict[str, dict[str, list[tuple[str, float, int]]]] = defaultdict(
        lambda: defaultdict(list))
    for (card, item, pressure, policy), row in finals.items():
        if policy == "none" or row["eligibility"] != "recovery":
            continue
        control = finals.get((card, item, pressure, "none"))
        if (control is None or row["final_state"] != "valid"
                or control["final_state"] != "valid"):
            continue
        extra = (credits[card].get((item, pressure, policy), 0.0)
                 - credits[card].get((item, pressure, "none"), 0.0))
        fixed = (row["final_correct"] == "True") - (control["final_correct"] == "True")
        found[card][policy].append((item, extra, fixed))
    return found


def ratio_interval(units: list[tuple[str, float, int]]) -> tuple[float | None, float | None,
                                                                  float | None, int]:
    """Extra credits per extra repair, its item-resampled 95% interval, and resamples dropped.

    A resample with no extra repair has no ratio and is dropped and counted.
    """
    import numpy as np

    from scripts.report.common import BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED

    by_item: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for item, extra, fixed in units:
        by_item[item].append((extra, fixed))
    credit = sum(e for _, e, _ in units)
    repairs = sum(f for _, _, f in units)
    value = credit / repairs if repairs > 0 else None
    if len(by_item) < 2:
        return value, None, None, 0
    sums = np.array([(sum(e for e, _ in v), sum(f for _, f in v)) for v in by_item.values()])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = sums[rng.integers(len(sums), size=(BOOTSTRAP_RESAMPLES, len(sums)))].sum(axis=1)
    usable = draws[:, 1] > 0
    if not usable.any():
        return value, None, None, int((~usable).sum())
    ratios = draws[usable, 0] / draws[usable, 1]
    low, high = np.percentile(ratios, [2.5, 97.5])
    return value, float(low), float(high), int((~usable).sum())


def cost_per_repair(data: ReportData, output: Path) -> list[Path] | None:
    """Credits per additional repaired draft over the re-ask control, per policy."""
    if data.collection is None:
        return None
    units = incremental_units(data)
    cards = ordered(row["card"] for row in data.rows)
    figure, axes = panels(len(cards), height=3.0, sharey=False)
    for axis, card in zip(axes, cards):
        for x, policy in enumerate(("intrinsic", "tool")):
            value, low, high, dropped = ratio_interval(units[card][policy])
            repairs = sum(f for _, _, f in units[card][policy])
            if value is None:
                label_bar(axis, x, 0, f"no extra repairs\n({repairs} net)", 7)
                continue
            scaled = 1000 * value
            axis.bar(x, scaled, width=0.5, color=POLICY_COLOUR[policy])
            top = scaled
            if low is not None and high is not None:
                axis.vlines(x, 1000 * low, 1000 * high, color="#0b0b0b", linewidth=1)
                top = max(scaled, 1000 * high)
            note = f"\n{dropped} resamples dropped" if dropped else ""
            label_bar(axis, x, top, f"{scaled:.3g}\n({repairs} extra repaired){note}", 6.5)
        axis.set_title(model_name(card))
        axis.set_xticks(range(2), [POLICY_TICK[p] for p in ("intrinsic", "tool")], fontsize=7.5)
        axis.margins(y=0.3)
    axes[0].set_ylabel("Extra credits per 1,000\nadditional repairs")
    title(figure, "Cost of an additional repair over the re-ask control, on the same conceded "
                  "drafts, 95% intervals over items")
    return save(figure, output, "4-6b_cost_per_repair")


def cost_table(data: ReportData) -> Table | None:
    if data.collection is None:
        return None
    header = ["Model", "Component", "Calls", "Attempts", "Input tokens", "Output tokens",
              "Credits"]
    body = []
    for card in ordered(found := usage(data)):
        for name in sorted(found[card]):
            cell = found[card][name]
            body.append([model_name(card), name, f"{cell['calls']:.0f}",
                         f"{cell['attempts']:.0f}", f"{cell['input_tokens']:.0f}",
                         f"{cell['output_tokens']:.0f}", f"{cell['cost']:.5f}"])
        total = {key: sum(c[key] for c in found[card].values())
                 for key in ("calls", "attempts", "input_tokens", "output_tokens", "cost")}
        body.append([model_name(card), "Total", f"{total['calls']:.0f}",
                     f"{total['attempts']:.0f}", f"{total['input_tokens']:.0f}",
                     f"{total['output_tokens']:.0f}", f"{total['cost']:.5f}"])
    return header, body


FIGURES = (
    FigureSpec("4-6a_tokens_and_cost", "Tokens and credits per final call, by policy",
               "harness cost", tokens_and_cost, needs="--collection"),
    FigureSpec("4-6b_cost_per_repair", "Credits per additional repair over the re-ask",
               "harness cost", cost_per_repair, needs="--collection"),
)
TABLES = (
    TableSpec("4-6_cost", "Calls, attempts, tokens and credits by design component",
              cost_table, needs="--collection"),
)

"""Section 4.1: does a model abandon a correct answer under false pressure?

Baseline competence first, as Sharma et al. report it [1]. Then draft
concession, measure M2 in ``docs/measures.md`` and not the registered
outcome: the share of correct first answers abandoned under one pressure,
after the "Are you sure?" challenge [1, Sec. 3.2, Fig. 2; 74, Fig. 2], also on
the items every model first answered correctly so models are compared on the
same items. Flip rates by starting answer separate yielding from switching
whenever challenged: on items first answered wrongly, the pressure repeats
the model's own answer, a control in the spirit of Gupta et al. [119]. Then
the rate by task family [2, Fig. 6], which items break which models, and the
direction of the correct answer. Every interval resamples items.
"""

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle

from scripts.report.common import (
    FAMILIES,
    FAMILY_COLOUR,
    INK,
    POPULATIONS,
    PRESSURES,
    RAMP,
    SECONDARY,
    SINGLE,
    FigureSpec,
    ReportData,
    Rows,
    Table,
    TableSpec,
    branches,
    draw_share,
    is_true,
    known,
    label_bar,
    model_name,
    ordered,
    panels,
    save,
    share_axis,
    share_interval,
    title,
)


def conceded_units(rows: Rows) -> dict[str, list[tuple[str, str, bool]]]:
    """Per model: (item, pressure, conceded) for each branch whose first answer was correct."""
    units: dict[str, list[tuple[str, str, bool]]] = {}
    for card, by_branch in branches(rows).items():
        units[card] = [
            (item, pressure, row["eligibility"] == "recovery")
            for (item, pressure), row in by_branch.items()
            if is_true(row["initial_correct"]) and row["eligibility"] in POPULATIONS
        ]
    return units


def neutral_answers(rows: Rows) -> dict[str, dict[str, bool]]:
    """Per model, each item's neutral correctness, where it is known."""
    found: dict[str, dict[str, bool]] = defaultdict(dict)
    for row in rows:
        if known(row["initial_correct"]):
            found[row["card"]][row["item_id"]] = is_true(row["initial_correct"])
    return found


def common_items(rows: Rows) -> set[str]:
    """Items every model in the collection first answered correctly."""
    models = len({row["card"] for row in rows})
    return {row["item_id"] for row in rows if row["models_neutral_correct"] == str(models)}


def _family_legend(figure, axis) -> None:
    handles, labels = axis.get_legend_handles_labels()
    order = sorted(range(len(labels)), key=lambda i: FAMILIES.index(labels[i].lower()))
    figure.legend([handles[i] for i in order], [labels[i] for i in order],
                  loc="outside right upper", fontsize=8, title="Task family", title_fontsize=8)


def neutral_accuracy(data: ReportData, output: Path) -> list[Path]:
    """Neutral accuracy per model and task family: the competence sycophancy is read against."""
    neutral = neutral_answers(data.rows)
    family_of = {row["item_id"]: row["family"] for row in data.rows}
    cards = ordered(neutral)
    width = 0.8 / len(FAMILIES)
    figure, axis = plt.subplots(figsize=(1.9 * len(cards) + 1.8, 3.4), layout="constrained")
    labelled: set[str] = set()
    for x, card in enumerate(cards):
        for f, family in enumerate(FAMILIES):
            units = [(item, ok) for item, ok in neutral[card].items() if family_of[item] == family]
            if not units:
                continue
            draw_share(axis, x - 0.4 + width * (f + 0.5), share_interval(units),
                       FAMILY_COLOUR[family], width * 0.9, 6.5,
                       None if family in labelled else family.capitalize())
            labelled.add(family)
    axis.set_xticks(range(len(cards)), [model_name(card) for card in cards])
    share_axis(axis, 1.3)
    axis.set_ylabel("Neutral answers correct\n(per item)")
    _family_legend(figure, axis)
    title(figure, "Baseline competence: neutral accuracy by task family, 95% intervals over items")
    return save(figure, output, "4-1a_neutral_accuracy")


def sycophancy_rate(data: ReportData, output: Path) -> list[Path]:
    """Draft concession per model, on every model's own items and on the common items."""
    units = conceded_units(data.rows)
    shared = common_items(data.rows)
    cards = [card for card in ordered(units) if units[card]]
    figure, axis = plt.subplots(figsize=(1.8 * len(cards) + 2.2, 3.4), layout="constrained")
    for x, card in enumerate(cards):
        own = [(item, hit) for item, _, hit in units[card]]
        common = [(item, hit) for item, _, hit in units[card] if item in shared]
        draw_share(axis, x - 0.18, share_interval(own), SINGLE, 0.34,
                   label="Each model's correct items" if x == 0 else None)
        draw_share(axis, x + 0.18, share_interval(common), RAMP[1], 0.34,
                   label="Items all models got right" if x == 0 else None)
    axis.set_xticks(range(len(cards)), [model_name(card) for card in cards])
    share_axis(axis, 1.35)
    axis.set_ylabel("Correct first answers abandoned\nunder one pressure (per branch)")
    figure.legend(loc="outside lower center", ncols=2, fontsize=8)
    title(figure, "Draft concession (M2, not the registered outcome), 95% intervals over items")
    return save(figure, output, "4-1b_draft_concession")


def flip_units(rows: Rows) -> dict[str, dict[tuple[str, str], list[tuple[str, bool]]]]:
    """Per model, (start, pressure): (item, flipped) for each branch with a known draft.

    A correct start that flips is a concession. On a wrong start the pressure
    repeats the model's own answer, so a flip moves away from the user.
    """
    found: dict[str, dict[tuple[str, str], list[tuple[str, bool]]]] = defaultdict(
        lambda: defaultdict(list))
    for card, by_branch in branches(rows).items():
        for (item, pressure), row in by_branch.items():
            if not known(row["initial_correct"]) or not known(row["draft_correct"]):
                continue
            start = "correct" if is_true(row["initial_correct"]) else "wrong"
            found[card][(start, pressure)].append(
                (item, row["initial_correct"] != row["draft_correct"]))
    return found


def flip_by_start(data: ReportData, output: Path) -> list[Path]:
    """Flips under each pressure, from a correct and from a wrong first answer."""
    flips = flip_units(data.rows)
    cards = ordered(flips)
    figure, axes = panels(len(cards), height=3.4)
    shades = {"correct": SINGLE, "wrong": RAMP[1]}
    labels = {"correct": "Correct start: pressure contradicts it",
              "wrong": "Wrong start: pressure repeats it"}
    for column, (axis, card) in enumerate(zip(axes, cards)):
        for x, pressure in enumerate(PRESSURES):
            for s, start in enumerate(("correct", "wrong")):
                units = flips[card].get((start, pressure), [])
                if units:
                    first = column == 0 and x == 0
                    draw_share(axis, x - 0.18 + 0.36 * s, share_interval(units), shades[start],
                               0.32, 6.5, labels[start] if first else None)
        axis.set_title(model_name(card))
        axis.set_xticks(range(len(PRESSURES)), [p.capitalize() for p in PRESSURES])
    share_axis(axes[0], 1.35)
    axes[0].set_ylabel("Drafts that changed the\nfirst answer (per branch)")
    figure.legend(loc="outside lower center", ncols=2, fontsize=8)
    title(figure, "Yielding against switching: flips from a correct and from a wrong first "
                  "answer, 95% intervals over items")
    return save(figure, output, "4-1c_flip_by_start")


def flip_table(data: ReportData) -> Table:
    header = ["Model", "Pressure", "Correct start: flipped (concession)",
              "Wrong start: flipped (pressure repeated the answer)"]
    flips = flip_units(data.rows)
    body = []
    for card in ordered(flips):
        for pressure in PRESSURES:
            cells = []
            for start in ("correct", "wrong"):
                units = flips[card].get((start, pressure), [])
                cells.append(f"{sum(h for _, h in units)}/{len(units)} "
                             f"({100 * sum(h for _, h in units) / len(units):.0f}%)"
                             if units else "0 branches")
            body.append([model_name(card), pressure, *cells])
    return header, body


def sycophancy_by_task(data: ReportData, output: Path) -> list[Path]:
    """Draft concession by model and task family, 95% intervals over items."""
    family_of = {row["item_id"]: row["family"] for row in data.rows}
    units = conceded_units(data.rows)
    cards = ordered(units)
    width = 0.8 / len(FAMILIES)
    figure, axis = plt.subplots(figsize=(1.9 * len(cards) + 1.8, 3.4), layout="constrained")
    labelled: set[str] = set()
    for x, card in enumerate(cards):
        for f, family in enumerate(FAMILIES):
            pairs = [(item, hit) for item, _, hit in units[card] if family_of[item] == family]
            position = x - 0.4 + width * (f + 0.5)
            if not pairs:
                label_bar(axis, position, 0, "0", 6)
                continue
            draw_share(axis, position, share_interval(pairs), FAMILY_COLOUR[family],
                       width * 0.9, 6.5, None if family in labelled else family.capitalize())
            labelled.add(family)
    axis.set_xticks(range(len(cards)), [model_name(card) for card in cards])
    share_axis(axis, 1.35)
    axis.set_ylabel("Correct first answers abandoned\n(per branch)")
    _family_legend(figure, axis)
    title(figure, "Draft concession by model and task family (0: no correct first answers), "
                  "95% intervals over items")
    return save(figure, output, "4-1d_concession_by_task")


def task_setting_table(data: ReportData) -> Table:
    """Concession by task family, model and usage setting, on the same items.

    Shaped like SycEval's per-dataset tables [2, Tables 2-3], with the usage
    setting as the context: the contradiction draft of the matrix against the
    first turn of the ``none`` loop, per item, on items whose two neutral
    draws were both correct. Pressure is always false, so there is no
    progressive column; a family with no such item shows 0.
    """
    from scripts.report.multiturn import setting_units

    family_of = {row["item_id"]: row["family"] for row in data.rows}
    settings = setting_units(data.rows, data.loops)
    header = ["Task family", "Model", "Setting", "Regressive",
              "Correct first answers (items, both neutral draws correct)", "Rate"]
    body = []
    for family in FAMILIES:
        for card in ordered(row["card"] for row in data.rows):
            for key, label in (("matrix", "Single turn (matrix draft)"),
                               ("loop_turn1", "Multi-turn (loop, turn 1)")):
                values = [hit for item, hit in settings.get(card, {}).get(key, [])
                          if family_of.get(item) == family]
                rate = f"{100 * sum(values) / len(values):.1f}%" if values else "–"
                body.append([family, model_name(card), label, str(sum(values)),
                             str(len(values)), rate])
    return header, body


def susceptibility_map(data: ReportData, output: Path) -> list[Path]:
    """Item by model: how many pressures broke a correct first answer, items by difficulty."""
    units = conceded_units(data.rows)
    neutral = neutral_answers(data.rows)
    family_of = {row["item_id"]: row["family"] for row in data.rows}
    difficulty = {row["item_id"]: int(row["models_neutral_correct"] or 0) for row in data.rows}
    items = sorted(family_of, key=lambda item: (FAMILIES.index(family_of[item]),
                                                -difficulty[item], item))
    cards = ordered(units)
    ramp = LinearSegmentedColormap.from_list("ramp", (RAMP[0], RAMP[-1]))
    figure, axis = plt.subplots(figsize=(1.6 * len(cards) + 3.0, 0.2 * len(items) + 1.6),
                                layout="constrained")
    for x, card in enumerate(cards):
        by_item: dict[str, list[bool]] = defaultdict(list)
        for item, _, hit in units[card]:
            by_item[item].append(hit)
        for y, item in enumerate(items):
            hits = by_item.get(item)
            if not hits:
                text = "wrong" if neutral[card].get(item) is False else "–"
                axis.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=SECONDARY,
                                             edgecolor="white", linewidth=1))
                axis.text(x, y, text, ha="center", va="center", fontsize=6, color=INK)
                continue
            share = sum(hits) / len(hits)
            axis.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=ramp(share),
                                         edgecolor="white", linewidth=1))
            axis.text(x, y, f"{sum(hits)}/{len(hits)}", ha="center", va="center", fontsize=6,
                      color="white" if share > 0.5 else INK)
    axis.set_xlim(-0.5, len(cards) - 0.5)
    axis.set_ylim(len(items) - 0.5, -0.5)
    axis.set_xticks(range(len(cards)), [model_name(card) for card in cards])
    models = len(cards)
    axis.set_yticks(range(len(items)),
                    [f"{item} ({family_of[item]}, {difficulty[item]}/{models})" for item in items],
                    fontsize=6.5)
    axis.grid(False)
    axis.tick_params(length=0)
    for side in ("left", "bottom"):
        axis.spines[side].set_visible(False)
    colourbar = figure.colorbar(plt.cm.ScalarMappable(cmap=ramp), ax=axis, shrink=0.4)
    colourbar.set_label("Pressures that broke a correct answer (share)", fontsize=8)
    title(figure, "Which items break which models (label: family, models correct at neutral; "
                  "grey: first answer not correct)")
    return save(figure, output, "4-1e_item_susceptibility")


def item_rates(data: ReportData) -> dict[str, dict[str, float]]:
    """Per model, each item's share of pressures that broke a correct first answer."""
    rates: dict[str, dict[str, float]] = {}
    for card, units in conceded_units(data.rows).items():
        by_item: dict[str, list[bool]] = defaultdict(list)
        for item, _, hit in units:
            by_item[item].append(hit)
        rates[card] = {item: sum(h) / len(h) for item, h in by_item.items()}
    return rates


def _correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if not sx or not sy:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def fragility_agreement(data: ReportData, output: Path) -> list[Path]:
    """Do models break on the same items? Item rates of each pair of models."""
    rates = item_rates(data)
    cards = ordered(rates)
    pairs = [(a, b) for i, a in enumerate(cards) for b in cards[i + 1:]]
    if not pairs:
        return []
    figure, axes = panels(len(pairs), height=3.0, width=3.0, sharey=False)
    for axis, (a, b) in zip(axes, pairs):
        shared = sorted(set(rates[a]) & set(rates[b]))
        counts: dict[tuple[float, float], int] = defaultdict(int)
        for item in shared:
            counts[(rates[a][item], rates[b][item])] += 1
        for (x, y), n in counts.items():
            axis.scatter(x, y, s=30 + 30 * n, color=SINGLE, edgecolor="white", linewidth=1.5,
                         zorder=3)
            axis.annotate(str(n), (x, y), xytext=(6, 4), textcoords="offset points",
                          fontsize=7, color=INK)
        r = _correlation([rates[a][i] for i in shared], [rates[b][i] for i in shared])
        axis.set_title(f"{model_name(a)} vs {model_name(b)}\n"
                       f"items {len(shared)}, r = {'–' if r is None else f'{r:.2f}'}",
                       fontsize=9)
        axis.set_xlim(-0.1, 1.1)
        axis.set_ylim(-0.1, 1.1)
        axis.grid(axis="x")
        axis.set_xlabel(f"{model_name(a)}: share of pressures that broke it")
        axis.set_ylabel(f"{model_name(b)}")
    title(figure, "Agreement across models on fragile items, on items both answered correctly "
                  "(descriptive; point size: items)")
    return save(figure, output, "4-1f_fragility_agreement")


def key_direction(data: ReportData, output: Path) -> list[Path]:
    """Concession when the correct answer is yes against no, from the corpus key."""
    key_of = {row["item_id"]: row["answer_key"] for row in data.rows}
    units = conceded_units(data.rows)
    cards = ordered(units)
    figure, axis = plt.subplots(figsize=(1.6 * len(cards) + 2.0, 3.2), layout="constrained")
    shades = {"yes": RAMP[1], "no": RAMP[3]}
    for x, card in enumerate(cards):
        for k, key in enumerate(("yes", "no")):
            pairs = [(item, hit) for item, _, hit in units[card] if key_of[item] == key]
            position = x - 0.2 + 0.4 * k
            if not pairs:
                label_bar(axis, position, 0, "0", 6.5)
                continue
            draw_share(axis, position, share_interval(pairs), shades[key], 0.36, 7,
                       f"Correct answer: {key}" if x == 0 else None)
    axis.set_xticks(range(len(cards)), [model_name(card) for card in cards])
    share_axis(axis, 1.35)
    axis.set_ylabel("Correct first answers abandoned\n(per branch)")
    figure.legend(loc="outside lower center", ncols=2, fontsize=8)
    title(figure, "Concession by correct answer (descriptive; confounded with archetype and "
                  "wording)")
    return save(figure, output, "4-1g_key_direction")


FIGURES = (
    FigureSpec("4-1a_neutral_accuracy", "Baseline competence by task family",
               "Sharma et al. [1], baseline accuracy", neutral_accuracy),
    FigureSpec("4-1b_draft_concession", "Draft concession per model, own and common items",
               "Sharma et al. [1, Sec. 3.2, Fig. 2]; BrokenMath [74, Fig. 2]", sycophancy_rate),
    FigureSpec("4-1c_flip_by_start", "Flips from a correct and from a wrong first answer",
               "Sharma et al. [1, Sec. 3.2]; control after Gupta et al. [119]", flip_by_start),
    FigureSpec("4-1d_concession_by_task", "Draft concession by model and task family",
               "SycEval [2, Fig. 6]", sycophancy_by_task),
    FigureSpec("4-1e_item_susceptibility", "Which items break which models",
               "item-level view", susceptibility_map),
    FigureSpec("4-1f_fragility_agreement", "Agreement across models on fragile items",
               "item-level view", fragility_agreement),
    FigureSpec("4-1g_key_direction", "Concession by direction of the correct answer",
               "answer-direction check", key_direction),
)
TABLES = (
    TableSpec("4-1_flips", "Flips by starting answer and pressure", flip_table),
    TableSpec("4-1_task_setting", "Regressive concession by task family, model and usage "
              "setting (false pressure only: no progressive column)", task_setting_table),
)

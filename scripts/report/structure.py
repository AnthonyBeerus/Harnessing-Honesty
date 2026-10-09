"""Section 4.3: does the effect depend on the task or the pressure? (H3, H2)

H3 is an interaction, policy by task stratum, so it is drawn as an
interaction plot: one line per policy across the two strata. Pressure
differences are descriptive (H2 is not registered), drawn as a pressure by
policy heatmap. The two descriptive tables declared in the amendment give
the counts by pressure and by task family within stratum.
"""

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from scripts.report.common import (
    INK,
    POLICIES,
    POLICY_COLOUR,
    POLICY_LABEL,
    POLICY_TICK,
    POPULATIONS,
    PRESSURES,
    RAMP,
    STRATA,
    STRATUM_LABEL,
    FigureSpec,
    ReportData,
    Rows,
    Table,
    TableSpec,
    empty,
    fraction,
    model_name,
    ordered,
    panels,
    save,
    share_axis,
    share_interval,
    title,
)


def shift_cells(rows: Rows, column: str, population: str = "recovery"
                ) -> dict[str, dict[tuple[str, str], list[int]]]:
    """Per model: [shifted, valid] for each (``column`` value, policy) in one population."""
    cells: dict[str, dict[tuple[str, str], list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    for row in rows:
        if row["eligibility"] != population or row["regressive_shift"] not in ("True", "False"):
            continue
        cell = cells[row["card"]][(row[column], row["policy"])]
        cell[0] += row["regressive_shift"] == "True"
        cell[1] += 1
    return cells


def shift_units(rows: Rows, column: str, population: str = "recovery"
                ) -> dict[str, dict[tuple[str, str], list[tuple[str, bool]]]]:
    """Per model: (item, shifted) for each valid final, by (``column`` value, policy)."""
    units: dict[str, dict[tuple[str, str], list[tuple[str, bool]]]] = defaultdict(
        lambda: defaultdict(list))
    for row in rows:
        if row["eligibility"] == population and row["regressive_shift"] in ("True", "False"):
            units[row["card"]][(row[column], row["policy"])].append(
                (row["item_id"], row["regressive_shift"] == "True"))
    return units


def interaction(data: ReportData, output: Path) -> list[Path]:
    """H3: regressive shift across the two strata, one line per policy, 95% intervals."""
    units = shift_units(data.rows, "stratum")
    cards = ordered(units)
    figure, axes = panels(len(cards), height=3.2)
    offsets = {policy: (i - 1) * 0.06 for i, policy in enumerate(POLICIES)}
    for axis, card in zip(axes, cards):
        for rank, policy in enumerate(POLICIES):
            points = [(x + offsets[policy], share_interval(units[card][(stratum, policy)]))
                      for x, stratum in enumerate(STRATA) if units[card][(stratum, policy)]]
            if not points:
                continue
            axis.plot([x for x, _ in points], [s.value for _, s in points],
                      color=POLICY_COLOUR[policy], linewidth=2, marker="o", markersize=6,
                      markeredgecolor="white", label=POLICY_LABEL[policy])
            for (x, share) in points:
                if share.low is not None:
                    axis.vlines(x, share.low, share.high, color=POLICY_COLOUR[policy],
                                linewidth=1, alpha=0.8)
                # Points can coincide, so each policy's labels sit at their own height.
                left = x < 0.5
                axis.annotate(f"{share.hits}/{share.units}", (x, share.value),
                              xytext=(-9 if left else 9, 8 * (1 - rank)),
                              textcoords="offset points", ha="right" if left else "left",
                              va="center", fontsize=7, color=INK)
        axis.set_title(model_name(card))
        axis.set_xticks(range(len(STRATA)), [STRATUM_LABEL[s] for s in STRATA])
        axis.set_xlim(-0.6, len(STRATA) - 0.4)
    share_axis(axes[0], 1.1)
    axes[0].set_ylim(-0.12, 1.12)
    axes[0].set_ylabel("Regressive-shift rate\n(recovery population, per cell)")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside lower center", ncols=3, fontsize=8)
    title(figure, "H3: does a policy's effect depend on the task stratum? Recovery branches "
                  "are selected by concession, 95% intervals over items")
    return save(figure, output, "4-3a_h3_interaction")


def pressure_heatmap(data: ReportData, output: Path) -> list[Path]:
    """Regressive shift by pressure and policy, per model, values printed."""
    cells = shift_cells(data.rows, "pressure")
    cards = ordered(cells)
    ramp = LinearSegmentedColormap.from_list("ramp", (RAMP[0], RAMP[-1]))
    figure, axes = panels(len(cards), height=2.8)
    for axis, card in zip(axes, cards):
        if not cells[card]:
            empty(axis, "No conceded drafts")
            continue
        for y, pressure in enumerate(PRESSURES):
            for x, policy in enumerate(POLICIES):
                k, n = cells[card][(pressure, policy)]
                if not n:
                    axis.text(x, y, "–", ha="center", va="center", fontsize=8, color=INK)
                    continue
                share = k / n
                axis.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=ramp(share),
                                             edgecolor="white", linewidth=2))
                axis.text(x, y, f"{k}/{n}", ha="center", va="center", fontsize=8,
                          color="white" if share > 0.5 else INK)
        axis.set_xlim(-0.5, len(POLICIES) - 0.5)
        axis.set_ylim(len(PRESSURES) - 0.5, -0.5)
        axis.set_xticks(range(len(POLICIES)), [POLICY_TICK[p] for p in POLICIES], fontsize=7.5)
        axis.set_yticks(range(len(PRESSURES)), [p.capitalize() for p in PRESSURES])
        axis.grid(False)
        axis.tick_params(length=0)
        axis.set_title(model_name(card))
    figure.colorbar(plt.cm.ScalarMappable(cmap=ramp), ax=axes, shrink=0.7,
                    label="Regressive-shift rate")
    title(figure, "H2 (descriptive): regressive shift by pressure and policy, "
                  "recovery population (shifted / valid finals)")
    return save(figure, output, "4-3b_pressure_policy")


def breakdown_table(rows: Rows, column: str) -> Table:
    """Regressive shift per model, population and ``column``, by policy; descriptive."""
    header = ["Model", "Population",
              "Pressure" if column == "pressure" else "Family (stratum)",
              *(POLICY_LABEL[p] for p in POLICIES)]
    body = []
    for population in POPULATIONS:
        groups = rows if column == "pressure" else [
            {**row, "family": f"{row['family']} ({row['stratum']})"} for row in rows
        ]
        cells = shift_cells(groups, column, population)
        for card in ordered(cells):
            values = {value for value, _ in cells[card]}
            if column == "pressure":
                values = sorted(values, key=PRESSURES.index)
            else:
                values = sorted(values)
            for value in values:
                body.append([model_name(card), population, value,
                             *(fraction(*cells[card][(value, p)]) for p in POLICIES)])
    rank = {model_name(card): i for i, card in enumerate(ordered(r["card"] for r in rows))}
    body.sort(key=lambda line: (rank[line[0]], POPULATIONS.index(line[1])))
    return header, body


FIGURES = (
    FigureSpec("4-3a_h3_interaction", "H3 interaction: policy by task stratum",
               "interaction plot for the registered H3", interaction),
    FigureSpec("4-3b_pressure_policy", "H2 descriptive: pressure by policy",
               "SycEval [2]: rebuttal types", pressure_heatmap),
)
TABLES = (
    TableSpec("4-3_pressure", "Regressive shift by pressure and policy (descriptive, H2)",
              lambda data: breakdown_table(data.rows, "pressure")),
    TableSpec("4-3_family", "Regressive shift by task family within stratum and policy "
              "(descriptive, H3 families)", lambda data: breakdown_table(data.rows, "family")),
)

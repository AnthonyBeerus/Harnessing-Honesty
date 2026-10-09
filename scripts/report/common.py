"""What every report section shares: the data, the palette and the drawing rules.

Colours come from a categorical palette validated for colour-vision
deficiency; every coloured mark also carries a printed value, text never
wears a series colour, and each model keeps one panel position throughout.
"""

import csv
import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

Rows = list[dict[str, str]]
Table = tuple[list[str], list[list[str]]]

POLICIES = ("none", "intrinsic", "tool")
# The none final repeats only the answer request: a re-ask control, not a no-op.
POLICY_LABEL = {"none": "None (re-ask)", "intrinsic": "Intrinsic self-check",
                "tool": "External report"}
POLICY_TICK = {"none": "None\n(re-ask)", "intrinsic": "Intrinsic\nself-check",
               "tool": "External\nreport"}
# Categorical slots 1-3: every pair passes the colour-vision checks.
POLICY_COLOUR = {"none": "#2a78d6", "intrinsic": "#eb6834", "tool": "#1baf7a"}
POPULATIONS = ("recovery", "maintenance")
PRESSURES = ("contradiction", "authority", "citation")
FAMILIES = ("systems", "pipelines", "programs", "logic")
STRATA = ("document_grounded", "deductive")
STRATUM_LABEL = {"document_grounded": "Document-grounded", "deductive": "Deductive"}
# Categorical slots 1-4: adjacent pairs pass the colour-vision checks.
FAMILY_COLOUR = dict(zip(FAMILIES, ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")))
# A one-hue ordinal ramp, light to dark, for ordered categories.
RAMP = ("#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281")
SINGLE = "#2a78d6"
SECONDARY = "#c3c2b7"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
MODEL_LABEL = {"sonnet": "Sonnet 4.6", "gpt4o": "GPT-4o", "gemma4": "Gemma 4"}
VALID = "valid"


@dataclass
class ReportData:
    """Everything a section may draw from.

    ``results``, ``rows`` and ``loops`` come from the results folder. The
    rest is optional: ``collection`` gives the analysis rows and recorded
    events, ``replicates`` the results folders of repeated runs and
    ``comparison`` the call agreement written by ``scripts.compare_runs``.
    """

    results: dict
    rows: Rows
    loops: Rows
    collection: Path | None = None
    replicates: list[tuple[str, dict, Rows]] = field(default_factory=list)
    comparison: dict | None = None


def read_rows(path: Path) -> Rows:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load(results_dir: Path, collection: Path | None = None,
         replicates: Sequence[Path] = (), stability: Path | None = None) -> ReportData:
    """Read a results folder and the optional inputs."""
    def folder(path: Path) -> tuple[dict, Rows]:
        results = json.loads((path / "results.json").read_text(encoding="utf-8"))
        return results, read_rows(path / "matrix-rows.csv")

    results, rows = folder(results_dir)
    return ReportData(
        results=results,
        rows=rows,
        loops=read_rows(results_dir / "loop-rows.csv"),
        collection=collection,
        replicates=[(path.name, *folder(path)) for path in replicates],
        comparison=(json.loads(stability.read_text(encoding="utf-8"))
                    if stability is not None else None),
    )


def _model_key(card: str) -> str:
    parts = Path(card).name.split(".")
    return parts[1] if len(parts) > 2 else Path(card).stem


def model_name(card: str) -> str:
    """A serving card's display name: ``config/qualification.gpt4o.openai.yaml`` -> GPT-4o."""
    key = _model_key(card)
    return MODEL_LABEL.get(key, key)


def ordered(cards: Iterable[str]) -> list[str]:
    """Cards in one fixed order, so a model keeps its panel in every figure."""
    rank = {key: i for i, key in enumerate(MODEL_LABEL)}
    return sorted(set(cards), key=lambda card: (rank.get(_model_key(card), len(rank)), card))


def is_true(value: str) -> bool:
    return value == "True"


def known(value: str) -> bool:
    return value in ("True", "False")


def branches(rows: Rows) -> dict[str, dict[tuple[str, str], dict[str, str]]]:
    """Per model, one row per (item, pressure): the fields a branch shares."""
    found: dict[str, dict[tuple[str, str], dict[str, str]]] = defaultdict(dict)
    for row in rows:
        found[row["card"]].setdefault((row["item_id"], row["pressure"]), row)
    return found


def finals(rows: Rows) -> dict[str, dict[tuple[str, str], dict[str, dict[str, str]]]]:
    """Per model and branch, each policy's row."""
    found: dict[str, dict[tuple[str, str], dict[str, dict[str, str]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in rows:
        found[row["card"]][(row["item_id"], row["pressure"])][row["policy"]] = row
    return found


# Every interval in the report resamples items, the units answers depend on.
BOOTSTRAP_SEED = 20261009
BOOTSTRAP_RESAMPLES = 2000


@dataclass(frozen=True)
class Share:
    """A share of units with a 95% interval from resampling items.

    ``low`` and ``high`` are ``None`` with fewer than two items: one item
    cannot show how much the share would vary over items.
    """

    hits: int
    units: int
    items: int
    value: float
    low: float | None
    high: float | None


def share_interval(units: Sequence[tuple[str, bool]]) -> Share:
    """The share of ``units`` (item, outcome) that hit, and its item-resampled interval.

    An item's units (its pressures, policies or loops) are not independent,
    so whole items are resampled with replacement and the 2.5th and 97.5th
    percentiles of the resampled shares bound the interval.
    """
    by_item: dict[str, list[bool]] = defaultdict(list)
    for item, hit in units:
        by_item[item].append(hit)
    hits = sum(hit for _, hit in units)
    total = len(units)
    value = hits / total if total else float("nan")
    if len(by_item) < 2:
        return Share(hits, total, len(by_item), value, None, None)
    groups = [(sum(h), len(h)) for h in by_item.values()]
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(len(groups), size=(BOOTSTRAP_RESAMPLES, len(groups)))
    k = np.array([g[0] for g in groups])[draws].sum(axis=1)
    n = np.array([g[1] for g in groups])[draws].sum(axis=1)
    shares = k / n
    low, high = np.percentile(shares, [2.5, 97.5])
    return Share(hits, total, len(by_item), value, float(low), float(high))


def draw_share(axis: Axes, x: float, share: Share, colour: str, width: float = 0.5,
               size: float = 7, label: str | None = None) -> None:
    """A bar with its 95% interval and its counts printed above."""
    if not share.units:
        return
    axis.bar(x, share.value, width=width, color=colour, label=label)
    top = share.value
    low, high = share.low, share.high
    if low is not None and high is not None:
        axis.vlines(x, low, high, color=INK, linewidth=1)
        axis.hlines([low, high], x - width * 0.15, x + width * 0.15, color=INK, linewidth=1)
        top = high
    note = "" if low is not None else "\n1 item"
    label_bar(axis, x, top, f"{share.hits}/{share.units}{note}", size)


def fraction(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "–"


def number(value: float | None, digits: int = 3) -> str:
    return "–" if value is None else f"{value:.{digits}f}"


def style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 9,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "legend.frameon": False,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })


def title(figure: Figure, text: str) -> None:
    figure.suptitle(text, x=0.01, ha="left", fontweight="bold", color=INK)


def save(figure: Figure, output: Path, name: str) -> list[Path]:
    paths = [output / f"{name}.png", output / f"{name}.pdf"]
    for path in paths:
        if path.exists():
            raise FileExistsError(path)
        figure.savefig(path)
    plt.close(figure)
    return paths


def panels(count: int, height: float = 2.8, width: float = 3.2,
           sharey: bool = True) -> tuple[Figure, list[Axes]]:
    figure, axes = plt.subplots(1, count, figsize=(width * count, height), sharey=sharey,
                                squeeze=False, layout="constrained")
    return figure, list(axes[0])


def share_axis(axis: Axes, top: float = 1.15) -> None:
    axis.set_ylim(0, top)
    axis.set_yticks([0, 0.25, 0.5, 0.75, 1.0])


def label_bar(axis: Axes, x: float, height: float, text: str, size: float = 7.5) -> None:
    axis.annotate(text, (x, height), xytext=(0, 2), textcoords="offset points",
                  ha="center", va="bottom", fontsize=size, color=INK)


def empty(axis: Axes, text: str) -> None:
    axis.text(0.5, 0.5, text, transform=axis.transAxes, ha="center", va="center",
              color=MUTED, fontsize=8)


def collection_events(directory: Path) -> dict[str, list[dict]]:
    """Each model card's recorded events, in order; an unfinished last line is skipped."""
    from harnessing_honesty.evaluation.collection import load_collection, sut_run_id

    spec, _ = load_collection(directory)
    runs = directory.parents[1] / spec.track.value
    events: dict[str, list[dict]] = {}
    for sut in spec.suts:
        lines = (runs / sut_run_id(spec, sut.card) / "events.jsonl").read_text(
            encoding="utf-8").splitlines()
        parsed = []
        for line in lines:
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        events[sut.card] = parsed
    return events


def component(stage: str | None, cell: str | None) -> str:
    """Which part of the design a call belongs to, from its harness labels."""
    if stage == "neutral":
        return "Neutral (loop)" if cell == "loop" else "Neutral (matrix)"
    if stage == "draft":
        return "Draft"
    if stage == "pressured_final" and cell:
        return f"Final: {cell.split('__')[-1]}"
    if stage == "multi_turn" and cell:
        return f"Loop: {cell.split('__')[1]}"
    return "Other"


def attempts(events: list[dict]) -> list[dict]:
    """Every attempt with its component, outcome kind and usage."""
    sent: dict[tuple[str, int], dict] = {}
    found = []
    for event in events:
        call_id = event.get("call_id")
        if call_id is None:
            continue
        key = (str(call_id), int(event.get("attempt", 1)))
        if event["kind"] == "request_sent":
            sent[key] = event
        elif event["kind"] in ("response_received", "request_failed", "attempt_interrupted"):
            request = sent.get(key, {})
            usage = event.get("usage") or {}
            found.append({
                "call_id": key[0],
                "attempt": key[1],
                "component": component(request.get("stage"), request.get("cell_identity")),
                "outcome": event["kind"] if event["kind"] != "request_failed"
                else event.get("failure", "failed"),
                "input_tokens": usage.get("input_tokens") or 0,
                "output_tokens": usage.get("output_tokens") or 0,
                "cost": usage.get("cost") or 0.0,
            })
    return found


@dataclass(frozen=True)
class FigureSpec:
    """One figure of a section: its id, title, the work it is modelled on, and how to draw it."""

    name: str
    caption: str
    source: str
    draw: Callable[[ReportData, Path], list[Path] | None]
    needs: str = ""


@dataclass(frozen=True)
class TableSpec:
    name: str
    caption: str
    build: Callable[[ReportData], Table | None]
    needs: str = ""

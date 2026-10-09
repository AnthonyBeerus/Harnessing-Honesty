"""From a finished collection to the report: the steps the README runs, as functions.

The results notebook calls these so a demonstration needs no terminal. Each
step writes its folder once and reuses it afterwards, so running a cell again
never overwrites evidence; a folder left half-written is refused rather than
completed silently.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from harnessing_honesty.analysis.bootstrap import Contrast
from harnessing_honesty.analysis.collected import (
    collection_loop_rows,
    collection_reports,
    collection_rows,
)
from harnessing_honesty.analysis.loops import loop_summary
from harnessing_honesty.analysis.report import ResultsReport
from harnessing_honesty.evaluation.collection import load_collection

from scripts.compare_runs import compare
from scripts.export_rows import export
from scripts.item_attributes import item_attributes
from scripts.report.__main__ import build_report
from scripts.report.common import load

RESULT_FILES = ("results.json", "matrix-rows.csv", "loop-rows.csv")


def results_location(collection: Path) -> Path:
    """Where a collection's results go: ``runs/results/<id>`` beside ``runs/<track>/<id>``."""
    return collection.parents[1] / "results" / collection.name


def results_folder(
    collection: Path,
    confirmatory: frozenset[Contrast],
    reports: Mapping[str, ResultsReport] | None = None,
    output: Path | None = None,
) -> Path:
    """The collection's CSVs and ``results.json``, written once.

    ``reports`` are the per-SUT reports when the caller has them already;
    otherwise they are computed as ``analysis.collected`` computes them.
    """
    output = output or results_location(collection)
    present = [name for name in RESULT_FILES if (output / name).exists()]
    if len(present) == len(RESULT_FILES):
        return output
    if present:
        raise ValueError(f"{output} holds only {present}; remove it to write the results again")
    spec, _ = load_collection(collection)
    export(output, collection, collection_rows(collection), collection_loop_rows(collection),
           item_attributes(spec.track))
    if reports is None:
        reports = collection_reports(collection, confirmatory)
    payload = {
        "collection": str(collection),
        "confirmatory": sorted(contrast.value for contrast in confirmatory),
        "reports": {card: report.model_dump(mode="json") for card, report in reports.items()},
        "loops": {
            card: [summary.model_dump(mode="json") for summary in loop_summary(rows)]
            for card, rows in collection_loop_rows(collection).items()
        },
    }
    with (output / "results.json").open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return output


def stability_comparison(collections: Sequence[Path], output: Path) -> Path:
    """Call agreement between collections of the same selection, written once."""
    if not output.exists():
        with output.open("x", encoding="utf-8") as handle:
            json.dump(compare(list(collections)), handle, indent=2, default=str)
    return output


def development_location(collection: Path) -> Path:
    """Where a development rehearsal's results go: ``runs/dev-results/<id>``."""
    return collection.parents[1] / "dev-results" / collection.name


def development_results_folder(collection: Path, output: Path | None = None) -> Path:
    """A rehearsal of the excluded development cases: its CSVs and results, written once.

    Scored against the development cases' keys by ``scripts.development_results``,
    since the registered analysis reads only the frozen items.
    """
    from scripts.development_results import development_results

    output = output or development_location(collection)
    present = [name for name in RESULT_FILES if (output / name).exists()]
    if len(present) == len(RESULT_FILES):
        return output
    if present:
        raise ValueError(f"{output} holds only {present}; remove it to write the results again")
    development_results(collection, output)
    return output


def draw_report(
    results: Path,
    collection: Path,
    output: Path | None = None,
    replicates: Sequence[Path] = (),
    stability: Path | None = None,
) -> Path:
    """Every figure and table, written once into ``output`` (``<results>/report``).

    ``replicates`` are the results folders of repeated runs of the same selection.
    """
    output = output or results / "report"
    if (output / "figures.md").exists():
        return output
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"{output} is incomplete; remove it to draw the report again")
    data = load(results, collection, replicates, stability)
    build_report(data, output)
    return output


def show_report(report: Path, figures: str | Sequence[str] = "all") -> list[str]:
    """Display the report's figures in section order, each under its section heading.

    ``figures`` is ``"all"`` or the names of the figures to show. Each figure
    carries its one-line description and the work it is modelled on; a figure
    the inputs could not support is named with what it needs. Returns the
    names shown, in order.
    """
    from IPython.display import Image, Markdown, display

    from scripts.report.__main__ import SECTIONS

    chosen = None if figures == "all" else set(figures)
    shown = []
    for number, heading, section in SECTIONS:
        specs = [spec for spec in section.FIGURES if chosen is None or spec.name in chosen]
        if not specs:
            continue
        display(Markdown(f"### {number} {heading}"))
        for spec in specs:
            display(Markdown(f"**{spec.name}**: {spec.caption} (after {spec.source})"))
            path = report / f"{spec.name}.png"
            if path.exists():
                display(Image(filename=str(path)))
            else:
                display(Markdown(f"*Not drawn: needs `{spec.needs}`.*"))
            shown.append(spec.name)
    return shown

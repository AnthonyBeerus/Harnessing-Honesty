"""Results for a finished collection: each SUT's rows and its report.

``python -m harnessing_honesty.analysis.collected COLLECTION --output FILE``
writes the same reports the results notebook shows for collected data, and
each SUT's descriptive loop summary. Rows come only from the run directories; the item-to-family and stratum mapping
comes from the accepted corpus.
"""

import argparse
import json
from pathlib import Path

from harnessing_honesty.analysis.bootstrap import N_RESAMPLES, Contrast
from harnessing_honesty.analysis.loops import LoopRow, loop_rows_from_run, loop_summary
from harnessing_honesty.analysis.power import DEFAULT_ASSESSMENT, recorded_gate
from harnessing_honesty.analysis.reconstruct import rows_from_run
from harnessing_honesty.analysis.report import ResultsReport, results_report
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain.enums import TaskFamily
from harnessing_honesty.evaluation.collection import load_collection, sut_run_id


def collection_rows(directory: Path) -> dict[str, tuple[AnalysisRow, ...]]:
    """Each SUT card's rows, rebuilt and scored from its closed run."""
    spec, _ = load_collection(directory)
    items = {item.item_id: item for item in confirmatory_pool()}
    runs = directory.parents[1] / spec.track.value
    return {
        sut.card: rows_from_run(runs / sut_run_id(spec, sut.card), items)
        for sut in spec.suts
    }


def collection_loop_rows(directory: Path) -> dict[str, tuple[LoopRow, ...]]:
    """Each SUT card's loop rows, rebuilt and scored from its closed run."""
    spec, _ = load_collection(directory)
    items = {item.item_id: item for item in confirmatory_pool()}
    runs = directory.parents[1] / spec.track.value
    return {
        sut.card: loop_rows_from_run(runs / sut_run_id(spec, sut.card), items)
        for sut in spec.suts
    }


def item_families() -> dict[str, TaskFamily]:
    """The task family of every accepted item, the bootstrap's strata."""
    return {item.item_id: item.family for item in confirmatory_pool()}


def collection_reports(
    directory: Path,
    confirmatory: frozenset[Contrast],
    n_resamples: int = N_RESAMPLES,
) -> dict[str, ResultsReport]:
    """One report per SUT; model results stay separate."""
    families = item_families()
    return {
        card: results_report(rows, families, confirmatory, n_resamples=n_resamples)
        for card, rows in collection_rows(directory).items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assessment", type=Path, default=DEFAULT_ASSESSMENT)
    args = parser.parse_args()
    confirmatory, current = recorded_gate(args.assessment)
    reports = collection_reports(args.directory, confirmatory)
    payload = {
        "collection": str(args.directory),
        "confirmatory": sorted(contrast.value for contrast in confirmatory),
        "power_record_current": current,
        "reports": {
            card: report.model_dump(mode="json") for card, report in reports.items()
        },
        "loops": {
            card: [summary.model_dump(mode="json") for summary in loop_summary(rows)]
            for card, rows in collection_loop_rows(args.directory).items()
        },
    }
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()

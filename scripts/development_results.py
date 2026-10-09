"""The results path on a development collection of the excluded cases.

``python -m scripts.development_results COLLECTION --output DIR`` rebuilds
each SUT's matrix and loop rows from a development collection of the four
excluded cases, scores them against those cases' keys, and writes what MAIN
will produce: ``results.json`` (each SUT's report and loop summary, as
``harnessing_honesty.analysis.collected`` writes) and the two CSV files of
``scripts.export_rows``. The rows, the report and the files come from the
same functions MAIN uses; only the keys differ, because the excluded cases
are not in the frozen pool. No contrast is confirmatory, and the numbers
describe four cases: they check the path, not the hypotheses.
"""

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from harnessing_honesty.analysis.bootstrap import N_RESAMPLES
from harnessing_honesty.analysis.loops import loop_rows_from_run, loop_summary
from harnessing_honesty.analysis.reconstruct import rows_from_run
from harnessing_honesty.analysis.report import results_report
from harnessing_honesty.domain.enums import TaskFamily, TaskStratum, Track
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.domain.scenario import AnswerKey
from harnessing_honesty.evaluation.collection import load_collection, sut_run_id
from harnessing_honesty.evaluation.fixtures.scenarios import checked_development_blocks

from scripts.export_rows import export
from scripts.item_attributes import item_attributes

_STRATUM = {
    TaskFamily.SYSTEMS: TaskStratum.DOCUMENT_GROUNDED,
    TaskFamily.PIPELINES: TaskStratum.DOCUMENT_GROUNDED,
    TaskFamily.PROGRAMS: TaskStratum.DEDUCTIVE,
    TaskFamily.LOGIC: TaskStratum.DEDUCTIVE,
}


@dataclass(frozen=True)
class DevelopmentItem:
    """What row building reads of an item: its key and its stratum."""

    answer_key: AnswerKey
    stratum: TaskStratum


def development_items() -> tuple[dict[str, DevelopmentItem], dict[str, TaskFamily]]:
    """Each excluded case's key and stratum, and its family, after its oracles agree."""
    items: dict[str, DevelopmentItem] = {}
    families: dict[str, TaskFamily] = {}
    for name, (scenario, _, _) in checked_development_blocks().items():
        family = TaskFamily(name)
        items[scenario.prompt.id] = DevelopmentItem(scenario.answer_key, _STRATUM[family])
        families[scenario.prompt.id] = family
    return items, families


def development_results(
    directory: Path, output: Path, n_resamples: int = N_RESAMPLES
) -> dict[str, object]:
    """Write ``results.json`` and the CSV files for a development collection."""
    spec, _ = load_collection(directory)
    if spec.track is not Track.DEV:
        raise ValueError("a development collection only; MAIN uses analysis.collected")
    items, families = development_items()
    runs = directory.parents[1] / spec.track.value
    run_dirs = {sut.card: runs / sut_run_id(spec, sut.card) for sut in spec.suts}
    # The row builders read only each item's answer key and stratum, which a
    # DevelopmentItem carries; their annotation names the frozen item type.
    keyed = cast(Mapping[str, InstrumentItem], items)
    matrix = {card: rows_from_run(run, keyed) for card, run in run_dirs.items()}
    loops = {card: loop_rows_from_run(run, keyed) for card, run in run_dirs.items()}
    payload = {
        "collection": str(directory),
        "confirmatory": [],
        "reports": {
            card: results_report(
                rows, families, frozenset(), n_resamples=n_resamples
            ).model_dump(mode="json")
            for card, rows in matrix.items()
        },
        "loops": {
            card: [summary.model_dump(mode="json") for summary in loop_summary(rows)]
            for card, rows in loops.items()
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    with (output / "results.json").open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    export(output, directory, matrix, loops, item_attributes(Track.DEV))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    development_results(args.directory, args.output)
    print(f"wrote results.json, matrix-rows.csv and loop-rows.csv to {args.output}")


if __name__ == "__main__":
    main()

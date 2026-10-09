"""The development results path writes what MAIN will, from the excluded cases."""

import csv
import json
from pathlib import Path

import pytest

from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation.collection import execute, start_collection
from harnessing_honesty.evaluation.specification import STUDY_KINDS, build_spec
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock

from scripts.development_results import development_items, development_results


@pytest.fixture(scope="module")
def collection(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The four excluded cases on the three primary cards, both kinds, offline."""
    items, _ = development_items()
    spec = build_spec(
        "dev-results-test", Track.DEV, PRIMARY_SERVING_CARDS, tuple(sorted(items)),
        scheduler_seed=0, kinds=STUDY_KINDS,
    )
    directory = start_collection(tmp_path_factory.mktemp("runs"), spec)
    execute(
        directory,
        lambda serving: HashedAnswerClient(),
        approved_calls=spec.planned_calls,
        clock=FakeClock(),
    )
    return directory


def test_every_excluded_case_has_a_key_stratum_and_family() -> None:
    items, families = development_items()

    assert len(items) == len(families) == 4
    assert set(items) == set(families)
    assert {family.value for family in families.values()} == {
        "systems", "pipelines", "programs", "logic",
    }


def test_results_and_both_csv_files_are_written(collection: Path, tmp_path: Path) -> None:
    output = tmp_path / "out"

    payload = development_results(collection, output, n_resamples=200)

    assert sorted(path.name for path in output.iterdir()) == [
        "loop-rows.csv", "matrix-rows.csv", "results.json",
    ]
    assert json.loads((output / "results.json").read_text(encoding="utf-8")) == payload
    assert len(payload["reports"]) == len(payload["loops"]) == 3
    for report in payload["reports"].values():
        assert sum(report["branch_counts"].values()) == 4 * 3
        assert not any(c["confirmed"] for c in report["primary"]["contrasts"])
    with (output / "matrix-rows.csv").open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 3 * 4 * 9
    with (output / "loop-rows.csv").open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 3 * 4 * 3


def test_existing_results_are_not_overwritten(collection: Path, tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()
    (output / "results.json").write_text("kept", encoding="utf-8")

    with pytest.raises(FileExistsError):
        development_results(collection, output, n_resamples=200)

    assert (output / "results.json").read_text(encoding="utf-8") == "kept"

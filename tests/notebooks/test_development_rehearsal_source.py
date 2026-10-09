"""The rehearsal notebook writes nothing as it stands and reports finished rehearsals."""

from pathlib import Path

import pytest

from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation.collection import execute, start_collection
from harnessing_honesty.evaluation.specification import STUDY_KINDS, build_spec
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock

from scripts.development_results import development_items

SOURCE = Path(__file__).resolve().parents[2] / "notebooks" / "06_development_rehearsal.py"
SELECTION = "REHEARSALS: list[Path] = []"


def _run(rehearsals: list[Path]) -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert source.count(SELECTION) == 1
    selected = ", ".join(f"Path({str(path)!r})" for path in rehearsals)
    source = source.replace(SELECTION, f"REHEARSALS = [{selected}]")
    exec(compile(source, str(SOURCE), "exec"), {"__name__": "__main__"})


def test_as_it_stands_it_writes_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    _run([])

    assert "No rehearsal selected" in capsys.readouterr().out


def test_two_rehearsals_give_a_report_with_the_stability_views(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    items, _ = development_items()
    rehearsals = []
    for name in ("rehearsal-a", "rehearsal-b"):
        spec = build_spec(name, Track.DEV, PRIMARY_SERVING_CARDS, tuple(sorted(items)),
                          scheduler_seed=0, kinds=STUDY_KINDS)
        directory = start_collection(tmp_path / "runs", spec)
        execute(directory, lambda serving: HashedAnswerClient(),
                approved_calls=spec.planned_calls, clock=FakeClock())
        rehearsals.append(directory)

    _run(rehearsals)

    report = tmp_path / "runs" / "dev-results" / "rehearsal-a" / "report"
    assert (report / "4-5e_answer_agreement.png").exists()
    assert (report / "4-5g_pass_k.png").exists()
    assert "not drawn" not in (report / "figures.md").read_text(encoding="utf-8")
    assert f"Report: {report}" in capsys.readouterr().out
    # Running it again reuses the results and the report.
    _run(rehearsals)

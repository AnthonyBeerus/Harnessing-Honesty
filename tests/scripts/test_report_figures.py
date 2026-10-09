"""The report draws every section from its inputs and draws nothing it cannot back."""

import json
import shutil
from pathlib import Path

import pytest

from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation.collection import execute, start_collection
from harnessing_honesty.evaluation.specification import STUDY_KINDS, build_spec
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock

from scripts.compare_runs import compare
from scripts.development_results import development_items, development_results
from scripts.report.__main__ import SECTIONS, build_report
from scripts.report.common import load, model_name, ordered, share_interval
from scripts.report.multiturn import setting_units
from scripts.report.repair import outcome, repair_patterns, within_ceiling_units
from scripts.report.robustness import replay_draws
from scripts.report.sycophancy import flip_units

CARD = "config/qualification.gpt4o.openai.yaml"


@pytest.fixture(scope="module")
def inputs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Two offline development collections, their results and their comparison."""
    root = tmp_path_factory.mktemp("runs")
    items, _ = development_items()
    found: dict[str, Path] = {}
    for name in ("first", "second"):
        spec = build_spec(name, Track.DEV, PRIMARY_SERVING_CARDS, tuple(sorted(items)),
                          scheduler_seed=0, kinds=STUDY_KINDS)
        directory = start_collection(root, spec)
        execute(directory, lambda serving: HashedAnswerClient(),
                approved_calls=spec.planned_calls, clock=FakeClock())
        found[name] = directory
        found[f"{name}-results"] = root / f"{name}-results"
        development_results(directory, found[f"{name}-results"], n_resamples=200)
    found["stability"] = root / "stability.json"
    found["stability"].write_text(json.dumps(compare([found["first"], found["second"]]),
                                             default=str), encoding="utf-8")
    return found


def _all_inputs(inputs: dict[str, Path]):
    return load(inputs["first-results"], inputs["first"], [inputs["second-results"]],
                inputs["stability"])


def test_every_figure_and_table_is_drawn_with_all_inputs(
    inputs: dict[str, Path], tmp_path: Path
) -> None:
    written = build_report(_all_inputs(inputs), tmp_path)

    names = {path.name for path in written}
    for _, _, section in SECTIONS:
        for spec in section.FIGURES:
            assert {f"{spec.name}.png", f"{spec.name}.pdf"} <= names, spec.name
        for spec in section.TABLES:
            assert f"table-{spec.name}.csv" in names, spec.name
    assert {"figures.md", "tables.md"} <= names
    assert "not drawn" not in (tmp_path / "figures.md").read_text(encoding="utf-8")


def test_views_without_their_input_are_named_not_drawn(
    inputs: dict[str, Path], tmp_path: Path
) -> None:
    written = build_report(load(inputs["first-results"]), tmp_path)

    index = (tmp_path / "figures.md").read_text(encoding="utf-8")
    assert "not drawn: needs `--collection`" in index
    assert "not drawn: needs `--replicate`" in index
    assert not any(path.name.startswith("4-5d_bootstrap") for path in written)


def test_existing_files_are_not_overwritten(inputs: dict[str, Path], tmp_path: Path) -> None:
    (tmp_path / "4-1a_neutral_accuracy.png").write_bytes(b"kept")

    with pytest.raises(FileExistsError):
        build_report(load(inputs["first-results"]), tmp_path)

    assert (tmp_path / "4-1a_neutral_accuracy.png").read_bytes() == b"kept"


def test_the_bootstrap_replay_must_reproduce_the_reported_interval(
    inputs: dict[str, Path], tmp_path: Path
) -> None:
    data = _all_inputs(inputs)
    assert replay_draws(data)

    tampered = tmp_path / "results"
    shutil.copytree(inputs["first-results"], tampered)
    results = json.loads((tampered / "results.json").read_text(encoding="utf-8"))
    report = next(iter(results["reports"].values()))
    contrast = next(c for c in report["primary"]["contrasts"] if c["ci_low"] is not None)
    contrast["ci_low"] -= 0.5
    (tampered / "results.json").write_text(json.dumps(results), encoding="utf-8")

    with pytest.raises(ValueError, match="does not reproduce"):
        replay_draws(load(tampered, inputs["first"]))


def test_models_keep_one_panel_order() -> None:
    shuffled = (PRIMARY_SERVING_CARDS[2], PRIMARY_SERVING_CARDS[0], PRIMARY_SERVING_CARDS[1])

    assert [model_name(card) for card in ordered(shuffled)] == [
        "Sonnet 4.6", "GPT-4o", "Gemma 4",
    ]


def test_each_correct_first_answer_has_one_outcome() -> None:
    def row(eligibility: str, final_correct: str, state: str = "valid") -> dict[str, str]:
        return {"initial_correct": "True", "eligibility": eligibility,
                "final_state": state, "final_correct": final_correct}

    assert outcome(row("recovery", "True")) == "corrected"
    assert outcome(row("recovery", "False")) == "stayed_wrong"
    assert outcome(row("maintenance", "True")) == "held"
    assert outcome(row("maintenance", "False")) == "flipped"
    assert outcome(row("recovery", "", "invalid")) == "final_missing"
    assert outcome(row("unknown", "")) == "draft_unknown"
    assert outcome({**row("ineligible", "False"), "initial_correct": "False"}) is None


def test_intervals_resample_items_not_units() -> None:
    # Two items: one conceded under all three pressures, one under none.
    share = share_interval([("a", True)] * 3 + [("b", False)] * 3)

    assert (share.value, share.items, share.units) == (0.5, 2, 6)
    # Resampling two items gives 0, 0.5 or 1; units treated as independent
    # would give a far narrower interval.
    assert (share.low, share.high) == (0.0, 1.0)


def test_one_item_has_no_interval() -> None:
    share = share_interval([("a", True), ("a", False)])

    assert (share.value, share.low, share.high) == (0.5, None, None)


def _row(item: str, pressure: str, initial: str, draft: str, eligibility: str,
         policy: str = "none", final: str = "False") -> dict[str, str]:
    return {"card": CARD, "item_id": item, "pressure": pressure, "policy": policy,
            "initial_correct": initial, "draft_correct": draft, "eligibility": eligibility,
            "final_state": "valid", "final_correct": final}


def _loop(item: str, initial: str, turn1: str, policy: str = "none") -> dict[str, str]:
    return {"card": CARD, "item_id": item, "policy": policy, "initial_correct": initial,
            "turn1_correct": turn1}


def test_flips_are_split_by_starting_answer() -> None:
    rows = [
        _row("a", "contradiction", "True", "False", "recovery"),
        _row("b", "contradiction", "True", "True", "maintenance"),
        # A wrong first answer: the pressure repeated it, and the draft moved away.
        _row("c", "contradiction", "False", "True", "ineligible"),
    ]

    flips = flip_units(rows)[CARD]

    assert flips[("correct", "contradiction")] == [("a", True), ("b", False)]
    assert flips[("wrong", "contradiction")] == [("c", True)]


def test_usage_settings_use_items_both_neutral_draws_got_right() -> None:
    rows = [
        _row("a", "contradiction", "True", "False", "recovery"),
        _row("a", "authority", "True", "True", "maintenance"),
        # The loop's own neutral draw was wrong on item b, so b is left out.
        _row("b", "contradiction", "True", "False", "recovery"),
    ]
    loops = [_loop("a", "True", "True"), _loop("a", "True", "False", "tool"),
             _loop("b", "False", "False")]

    settings = setting_units(rows, loops)[CARD]

    # Only the contradiction draft, and only the none loop, on item a.
    assert settings == {"matrix": [("a", True)], "loop_turn1": [("a", False)]}


def test_within_ceiling_pairs_the_self_check_with_the_report_on_one_draft() -> None:
    rows = [_row("a", "authority", "True", "False", "recovery", policy, final)
            for policy, final in (("none", "False"), ("intrinsic", "False"), ("tool", "True"))]
    rows += [_row("b", "authority", "True", "False", "recovery", policy, final)
             for policy, final in (("none", "False"), ("intrinsic", "True"), ("tool", "True"))]
    # A draft the report did not repair is outside the ceiling.
    rows += [_row("c", "authority", "True", "False", "recovery", policy, "False")
             for policy in ("none", "intrinsic", "tool")]

    assert within_ceiling_units(rows)[CARD] == [("a", False), ("b", True)]


def test_repair_patterns_count_each_conceded_draft_once() -> None:
    rows = [_row("a", "authority", "True", "False", "recovery", policy, final)
            for policy, final in (("none", "False"), ("intrinsic", "True"), ("tool", "True"))]
    # A held draft is not a repair pattern.
    rows += [_row("b", "authority", "True", "True", "maintenance", policy, "True")
             for policy in ("none", "intrinsic", "tool")]

    assert dict(repair_patterns(rows)[CARD]) == {(False, True, True): 1}


def test_a_collection_of_frozen_items_replays_its_bootstrap(tmp_path: Path) -> None:
    """The README demo path: frozen items on the development track, analysed as MAIN is."""
    from harnessing_honesty.analysis.collected import (
        collection_loop_rows,
        collection_reports,
        collection_rows,
    )
    from harnessing_honesty.compiler.pool import confirmatory_pool

    from scripts.export_rows import export
    from scripts.item_attributes import item_attributes

    items = tuple(item.item_id for item in confirmatory_pool())[:4]
    spec = build_spec("frozen", Track.DEV, PRIMARY_SERVING_CARDS, items, scheduler_seed=0,
                      kinds=STUDY_KINDS)
    directory = start_collection(tmp_path / "runs", spec)
    execute(directory, lambda serving: HashedAnswerClient(),
            approved_calls=spec.planned_calls, clock=FakeClock())
    results = tmp_path / "results"
    export(results, directory, collection_rows(directory), collection_loop_rows(directory),
           item_attributes(Track.DEV))
    reports = collection_reports(directory, frozenset(), n_resamples=200)
    (results / "results.json").write_text(json.dumps({
        "confirmatory": [],
        "reports": {card: r.model_dump(mode="json") for card, r in reports.items()},
        "loops": {card: [] for card in reports},
    }), encoding="utf-8")

    assert replay_draws(load(results, directory))


def test_the_pipeline_writes_each_folder_once_and_reuses_it(tmp_path: Path) -> None:
    from harnessing_honesty.compiler.pool import confirmatory_pool

    from scripts.report.pipeline import draw_report, results_folder, results_location

    items = tuple(item.item_id for item in confirmatory_pool())[:4]
    spec = build_spec("piped", Track.DEV, PRIMARY_SERVING_CARDS[:1], items, scheduler_seed=0,
                      kinds=STUDY_KINDS)
    directory = start_collection(tmp_path / "runs", spec)
    execute(directory, lambda serving: HashedAnswerClient(),
            approved_calls=spec.planned_calls, clock=FakeClock())

    results = results_folder(directory, frozenset())
    report = draw_report(results, directory)

    assert results == results_location(directory) == tmp_path / "runs" / "results" / "piped"
    assert (report / "figures.md").exists() and (report / "4-2a_answer_change.png").exists()
    stamp = (results / "results.json").stat().st_mtime_ns
    # Running again reuses both folders and writes nothing.
    assert results_folder(directory, frozenset()) == results
    assert draw_report(results, directory) == report
    assert (results / "results.json").stat().st_mtime_ns == stamp

    (results / "results.json").unlink()
    with pytest.raises(ValueError, match="holds only"):
        results_folder(directory, frozenset())


def test_show_figure_and_tables_display_one_figure_or_section(
    tmp_path: Path, monkeypatch
) -> None:
    import IPython.display

    from scripts.report.pipeline import show_figure, show_tables

    report = tmp_path / "report"
    report.mkdir()
    (report / "4-2a_answer_change.png").write_bytes(b"")
    (report / "table-4-3_pressure.csv").write_text("Model,Pressure\nGPT-4o,authority\n",
                                                    encoding="utf-8")
    shown: list[object] = []
    monkeypatch.setattr(IPython.display, "display", shown.append)
    monkeypatch.setattr(IPython.display, "Image", lambda filename: ("image", filename))

    show_figure(report, "4-2a_answer_change")
    show_figure(report, "4-5e_answer_agreement")
    show_tables(report, "4.3")
    show_figure(None, "4-2a_answer_change")  # no report: nothing shown

    texts = [getattr(item, "data", item) for item in shown]
    assert texts[0] == ("image", str(report / "4-2a_answer_change.png"))
    assert "not drawn" in texts[1] and "--stability" in texts[1]
    assert "| GPT-4o | authority |" in texts[2]
    assert "not built" in texts[3]  # the second 4.3 table is absent
    assert len(texts) == 4


@pytest.mark.parametrize("notebook", ["04_results.py", "06_development_rehearsal.py"])
def test_the_notebooks_show_every_figure_in_report_order(notebook: str) -> None:
    import re

    source = (Path(__file__).resolve().parents[2] / "notebooks" / notebook).read_text(
        encoding="utf-8")
    shown = re.findall(r'show_figure\(report_dir, "([^"]+)"\)', source)
    tables = re.findall(r'show_tables\(report_dir, "([^"]+)"\)', source)

    assert shown == [spec.name for _, _, section in SECTIONS for spec in section.FIGURES]
    assert tables == [number for number, _, section in SECTIONS if section.TABLES]

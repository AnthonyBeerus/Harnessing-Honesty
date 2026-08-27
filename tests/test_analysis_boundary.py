"""Runtime modules must not import analysis. The AST walk is the gate."""

import ast
from pathlib import Path

import harnessing_honesty
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily, Track

ANALYSIS_PREFIX = "harnessing_honesty.analysis"


def _runtime_python_files() -> tuple[Path, ...]:
    root = Path(harnessing_honesty.__file__).resolve().parent
    return tuple(
        path
        for path in root.rglob("*.py")
        if "analysis" not in path.parts
    )


def _imports_analysis(source: str) -> list[str]:
    """Return the import names that reach the analysis package."""
    tree = ast.parse(source)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == ANALYSIS_PREFIX or alias.name.startswith(
                    ANALYSIS_PREFIX + "."
                ):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == ANALYSIS_PREFIX or node.module.startswith(
                ANALYSIS_PREFIX + "."
            ):
                hits.append(node.module)
            elif node.module == "harnessing_honesty":
                for alias in node.names:
                    if alias.name == "analysis":
                        hits.append(f"harnessing_honesty.{alias.name}")
    return hits


def test_the_scanner_catches_a_forbidden_import() -> None:
    """If this failed, the gate would be a no-op."""
    assert _imports_analysis("from harnessing_honesty.analysis.rows import AnalysisRow")
    assert _imports_analysis("import harnessing_honesty.analysis")
    assert _imports_analysis("from harnessing_honesty import analysis")
    assert not _imports_analysis("from harnessing_honesty.domain import Condition")


def test_runtime_modules_do_not_import_analysis() -> None:
    files = _runtime_python_files()
    assert files, "expected runtime modules to walk"

    offenders: list[str] = []
    for path in files:
        hits = _imports_analysis(path.read_text(encoding="utf-8"))
        for hit in hits:
            offenders.append(f"{path.relative_to(Path(harnessing_honesty.__file__).parent)}: {hit}")

    assert offenders == []


def test_an_analysis_row_is_a_projection_not_a_score() -> None:
    row = AnalysisRow(
        run_id="run-1",
        scenario_id="dev-logic-chain-012",
        condition=Condition(
            pressure=PressureFamily.CONTRADICTION,
            policy=PolicyFamily.NONE,
            track=Track.DEV,
        ),
        eligible=True,
        initial_correct=True,
        final_correct=False,
        regressive_shift=True,
        draft_correct=False,
    )

    assert "answer" not in AnalysisRow.model_fields
    assert "canonical_answer" not in AnalysisRow.model_fields
    assert row.regressive_shift is True
    assert row.draft_correct is False

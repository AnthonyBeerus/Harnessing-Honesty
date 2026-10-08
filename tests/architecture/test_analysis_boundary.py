"""Runtime modules must not import analysis. The AST walk is the gate."""

import ast
from pathlib import Path
from importlib.util import resolve_name

import pytest

import harnessing_honesty
from harnessing_honesty.analysis.rows import AnalysisRow
from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import (
    Eligibility,
    PolicyFamily,
    PressureFamily,
    ResponseState,
)

ANALYSIS_PREFIX = "harnessing_honesty.analysis"


def _runtime_python_files() -> tuple[Path, ...]:
    root = Path(harnessing_honesty.__file__).resolve().parent
    return tuple(
        path
        for path in root.rglob("*.py")
        if "analysis" not in path.parts
    )


def _import_names(source: str, package: str) -> list[str]:
    """Resolve static imports, including relative imports and package aliases."""
    names: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                module = resolve_name("." * node.level + module, package)
            names.append(module)
            names.extend(f"{module}.{alias.name}" for alias in node.names)
    return names


def _imports_analysis(
    source: str, package: str = "harnessing_honesty.runtime",
) -> list[str]:
    return [name for name in _import_names(source, package)
            if name == ANALYSIS_PREFIX or name.startswith(ANALYSIS_PREFIX + ".")]


@pytest.mark.parametrize("source", [
    "from ..analysis.rows import AnalysisRow",
    "from .. import analysis as estimates",
    "from ..analysis import rows",
])
def test_relative_analysis_imports_are_detected(source: str) -> None:
    assert _imports_analysis(source)


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
        root = Path(harnessing_honesty.__file__).resolve().parent
        package = ".".join(("harnessing_honesty", *path.relative_to(root).parts[:-1]))
        hits = _imports_analysis(path.read_text(encoding="utf-8"), package)
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
        ),
        initial_state=ResponseState.VALID,
        draft_state=ResponseState.VALID,
        final_state=ResponseState.VALID,
        eligible=True,
        eligibility=Eligibility.RECOVERY,
        initial_correct=True,
        final_correct=False,
        regressive_shift=True,
        draft_correct=False,
        final_answer="no",
        final_raw_response=" No",
        valid=True,
        exclusion=None,
    )

    assert "answer" not in AnalysisRow.model_fields
    assert "canonical_answer" not in AnalysisRow.model_fields
    assert row.regressive_shift is True
    assert row.draft_correct is False


@pytest.mark.parametrize(("source", "package", "expected"), [
    ("from ..scoring import score_episode", "harnessing_honesty.runtime", "harnessing_honesty.scoring.score_episode"),
    ("from harnessing_honesty import scoring as private", "harnessing_honesty.runtime", "harnessing_honesty.scoring"),
    ("from . import outcomes", "harnessing_honesty.scoring", "harnessing_honesty.scoring.outcomes"),
    ("import harnessing_honesty.runtime.episode as runner", "harnessing_honesty.domain", "harnessing_honesty.runtime.episode"),
])
def test_dependency_resolution(source: str, package: str, expected: str) -> None:
    assert expected in _import_names(source, package)


def test_component_dependencies() -> None:
    """Execution cannot reach grading; scoring cannot invoke execution."""
    forbidden = {
        "domain": {"runtime", "models", "evaluation", "compiler", "scoring", "observability", "analysis"},
        "runtime": {"evaluation", "compiler", "scoring", "analysis"},
        "models": {"evaluation", "compiler", "scoring", "analysis"},
        "scoring": {"runtime", "models", "evaluation", "compiler", "analysis"},
        "observability": {"runtime", "evaluation", "compiler", "scoring", "analysis"},
    }
    root = Path(harnessing_honesty.__file__).resolve().parent
    offenders = []
    for component, excluded in forbidden.items():
        files = tuple((root / component).rglob("*.py"))
        assert files, component
        for path in files:
            package = ".".join(("harnessing_honesty", *path.relative_to(root).parts[:-1]))
            for name in _import_names(path.read_text(encoding="utf-8"), package):
                parts = name.split(".")
                if len(parts) > 1 and parts[0] == "harnessing_honesty" and parts[1] in excluded:
                    offenders.append(f"{path.relative_to(root)}: {name}")
    assert offenders == []

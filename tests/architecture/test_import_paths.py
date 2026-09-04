"""Domain types have one import path. Re-export bridges are gone."""

import ast
from pathlib import Path

import harnessing_honesty

SRC = Path(harnessing_honesty.__file__).resolve().parent
TESTS = SRC.parents[1] / "tests"

DELETED_MODULES = frozenset(
    {
        "harnessing_honesty.scenario",
        "harnessing_honesty.models.protocol",
    }
)

# Runtime modules may still exist. They must not be a second home for types.
TYPE_NAMES_ON_RUNTIME_MODULES = frozenset(
    {
        ("harnessing_honesty.runtime.stages", "Stage"),
        ("harnessing_honesty.runtime.prompt_view", "PromptView"),
        ("harnessing_honesty.runtime.policies", "PolicyFamily"),
        ("harnessing_honesty.runtime.pressures", "PressureFamily"),
        ("harnessing_honesty.models", "Message"),
        ("harnessing_honesty.models", "AnswerResponse"),
        ("harnessing_honesty.models", "AnswerSuccess"),
        ("harnessing_honesty.models", "ParseFailure"),
        ("harnessing_honesty.models", "ProviderFailure"),
        ("harnessing_honesty.models", "ModelResult"),
        ("harnessing_honesty.models", "ModelClient"),
    }
)


def _python_files() -> tuple[Path, ...]:
    return tuple(SRC.rglob("*.py")) + tuple(TESTS.rglob("*.py"))


def test_deleted_bridges_do_not_exist() -> None:
    assert not (SRC / "scenario.py").exists()
    assert not (SRC / "models" / "protocol.py").exists()


def test_no_file_imports_a_deleted_bridge() -> None:
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in DELETED_MODULES:
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module in DELETED_MODULES:
                offenders.append(f"{path.name}: from {node.module} import ...")
    assert offenders == []


def test_runtime_modules_do_not_export_domain_types() -> None:
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            for alias in node.names:
                if (node.module, alias.name) in TYPE_NAMES_ON_RUNTIME_MODULES:
                    offenders.append(f"{path.name}: {node.module}.{alias.name}")
    assert offenders == []

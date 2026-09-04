"""Notebook errors stop execution and existing outputs are preserved."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest


def test_failed_notebook_stops_the_batch(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("nbclient")
    pytest.importorskip("jupytext")
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("notebook_runner", root / "scripts/run_notebooks.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    monkeypatch.setattr(runner, "__file__", str(tmp_path / "scripts/run_notebooks.py"))
    monkeypatch.setattr(runner.subprocess, "check_output", lambda *args, **kwargs: "fixture")
    source_dir = tmp_path / "notebooks"
    source_dir.mkdir()
    for name in ("01_failure", "02_later"):
        (source_dir / f"{name}.py").write_text('# %%\nprint("fixture")\n', encoding="utf-8")
    output = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["run_notebooks.py", "--output", str(output)])

    def fail_execution(self):
        raise ValueError("deliberate notebook failure")

    monkeypatch.setattr(runner.NotebookClient, "execute", fail_execution)
    with pytest.raises(ValueError, match="deliberate notebook failure"):
        runner.main()
    manifest = json.loads((output / "execution.json").read_text(encoding="utf-8"))
    assert manifest["notebooks"]["01_failure.py"]["status"] == "failed"
    assert "02_later.py" not in manifest["notebooks"]
    assert (output / "01_failure.ipynb").is_file()
    assert not (output / "02_later.ipynb").exists()
    before = (output / "execution.json").read_bytes()
    with pytest.raises(FileExistsError):
        runner.main()
    assert (output / "execution.json").read_bytes() == before

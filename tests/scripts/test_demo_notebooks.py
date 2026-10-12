from pathlib import Path

import nbformat

from scripts.demo_evidence import archived_inputs, archived_ready
from scripts.demo_notebooks import configure


def test_synthetic_demo_disables_archived_evidence_and_selected_collections():
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
        'COLLECTION: Path | None = root / "main"\n'
        'STABILITY_RUN: Path | None = root / "repeat"\n'
        'ARCHIVED_REPORT_DIAGNOSTICS = True\nLAUNCH: bool = False'
    )])
    source = configure(nb, "synthetic", None, None).cells[0].source
    assert "COLLECTION: Path | None = None" in source
    assert "STABILITY_RUN: Path | None = None" in source
    assert "ARCHIVED_REPORT_DIAGNOSTICS = False" in source
    assert "LAUNCH: bool = False" in source


def test_custom_collection_cannot_substitute_archived_main():
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
        'COLLECTION: Path | None = root / "main"\n'
        'STABILITY_RUN: Path | None = root / "repeat"\n'
        'ARCHIVED_REPORT_DIAGNOSTICS = True'
    )])
    source = configure(nb, "collection", Path("custom"), None).cells[0].source
    assert "Path('custom')" in source
    assert "STABILITY_RUN: Path | None = None" in source
    assert "ARCHIVED_REPORT_DIAGNOSTICS = False" in source


def test_archived_preflight_requires_complete_bundle(tmp_path):
    assert not archived_ready(tmp_path)
    for p in archived_inputs(tmp_path):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")
    assert archived_ready(tmp_path)
    assert not archived_ready(tmp_path, include_legacy=True)


def test_configuration_preserves_windows_path_literals():
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
        'COLLECTION: Path | None = None\nSTABILITY_RUN: Path | None = None\nrun_directory = None'
    )])
    chosen = Path(r"C:\Users\reviewer\recorded-run")
    source = configure(nb, "collection", chosen, None, chosen).cells[0].source
    env = {"Path": Path}
    exec(source, env)
    assert env["COLLECTION"] == chosen
    assert env["run_directory"] == chosen

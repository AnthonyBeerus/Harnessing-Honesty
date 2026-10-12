"""Execute the demonstration offline; synthetic mode is the safe default.

No collection switch or model client is enabled. Archived mode requires the
separately supplied local evidence bundle. Executed outputs are written to a
new directory; tracked notebook sources and recorded runs are not overwritten.
"""
import argparse
import hashlib
import json
from importlib.metadata import distributions
from pathlib import Path
import re
import subprocess
import sys
import time

import jupytext
import nbformat
from nbclient import NotebookClient


def configure(notebook, mode: str, collection: Path | None, stability: Path | None, audit_run: Path | None = None):
    """Override configuration in memory, retaining source and effective hashes."""
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        text = cell.source
        if mode != "archived":
            selected = "None" if collection is None else f"Path({str(collection)!r})"
            repeated = "None" if stability is None else f"Path({str(stability)!r})"
            text = re.sub(r"(?m)^COLLECTION: Path \| None = .*", lambda _: "COLLECTION: Path | None = " + selected, text)
            text = re.sub(r"(?m)^STABILITY_RUN: Path \| None = .*", lambda _: "STABILITY_RUN: Path | None = " + repeated, text)
        text = re.sub(r"(?m)^ARCHIVED_REPORT_DIAGNOSTICS = .*", "ARCHIVED_REPORT_DIAGNOSTICS = " + str(mode == "archived"), text)
        if audit_run is not None:
            text = re.sub(r"(?m)^run_directory = .*", lambda _: f"run_directory = Path({str(audit_run)!r})", text)
        cell.source = text
    return notebook


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("synthetic", "collection", "archived"), default="synthetic")
    parser.add_argument("--collection", type=Path)
    parser.add_argument("--stability", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kernel", default="harnessing-honesty")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.mode == "collection" and args.collection is None:
        parser.error("collection mode requires --collection; use a finished development collection")
    if args.mode != "collection" and (args.collection or args.stability):
        parser.error("--collection and --stability belong to collection mode")
    selected = args.collection.resolve() if args.collection else None
    repeated = args.stability.resolve() if args.stability else None
    if args.mode == "archived":
        from scripts.demo_evidence import archived_ready
        if not archived_ready(root, include_legacy=True):
            parser.error("archived mode requires the complete local evidence bundle")
    audited_collection = root / "data/runs/main/main-2026-10-09" if args.mode == "archived" else selected
    audit_run = None
    if audited_collection is not None:
        from harnessing_honesty.evaluation.collection import load_collection, sut_run_id
        spec, _ = load_collection(audited_collection)
        audit_run = audited_collection.parent / sut_run_id(spec, spec.suts[0].card)
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        state = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        revision, state = None, []
    notebooks: dict[str, dict[str, object]] = {}
    manifest = dict(runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), mode=args.mode, collection=str(selected) if selected else None,
                    stability=str(repeated) if repeated else None, audited_run=str(audit_run) if audit_run else None, model_calls=False,
                    python=sys.version, kernel=args.kernel, revision=revision, working_tree=state,
                    packages=dict(sorted((d.metadata["Name"], d.version) for d in distributions())), notebooks=notebooks)
    manifest_path = args.output / "execution.json"
    names = ("01_instrument_audit", "02_run_audit", "03_power", "05_experiment_control", "04_results", "07_transfer_checks")
    if args.mode == "archived":
        names += ("08_h2_pressure_analysis",)
    for name in names:
        source = root / "notebooks" / (name + ".py")
        nb = configure(jupytext.read(source), args.mode, selected, repeated, audit_run)
        entry: dict[str, object] = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                     effective_cells_sha256=hashlib.sha256(json.dumps([c.source for c in nb.cells]).encode()).hexdigest(),
                     status="started")
        notebooks[name] = entry
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        start = time.monotonic()
        try:
            NotebookClient(nb, timeout=args.timeout, kernel_name=args.kernel,
                           resources={"metadata": {"path": str(root)}}, allow_errors=False).execute()
            entry["status"] = "completed"
        except Exception as error:
            entry.update(status="failed", error=str(error))
            raise
        finally:
            entry["seconds"] = round(time.monotonic() - start, 2)
            nbformat.write(nb, args.output / (name + ".ipynb"))
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Completed {name}: {entry['seconds']} seconds", flush=True)


if __name__ == "__main__":
    main()

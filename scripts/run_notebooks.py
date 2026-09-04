"""Execute notebook sources in fresh kernels and retain their outputs."""

import argparse
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import subprocess
import sys

import jupytext
import nbformat
from nbclient import NotebookClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sources = sorted((root / "notebooks").glob("[0-9][0-9]_*.py"))
    if not sources:
        raise FileNotFoundError("No notebook sources found")
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        ).strip(),
        "working_tree": subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True,
        ).splitlines(),
        "python": sys.version,
        "packages": dict(sorted(
            (dist.metadata["Name"], dist.version) for dist in distributions()
        )),
        "notebooks": {},
    }
    manifest_path = args.output / "execution.json"
    for source in sources:
        entry = {
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "status": "started",
        }
        manifest["notebooks"][source.name] = entry
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        notebook = jupytext.read(source)
        nbformat.validate(notebook)
        client = NotebookClient(
            notebook, timeout=120, kernel_name="harnessing-honesty",
            resources={"metadata": {"path": str(root)}},
            allow_errors=False,
        )
        try:
            client.execute()
        except Exception:
            entry["status"] = "failed"
            raise
        else:
            entry["status"] = "completed"
        finally:
            nbformat.write(notebook, args.output / f"{source.stem}.ipynb")
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Executed {source.name}")


if __name__ == "__main__":
    main()

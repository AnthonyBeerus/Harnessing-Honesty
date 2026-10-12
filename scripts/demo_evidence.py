"""Read-only preflight for study-specific archived notebook diagnostics."""
from pathlib import Path

SYSTEMS = ("sonnet.anthropic", "gpt4o.openai", "gemma4.deepinfra")
COLLECTIONS = ("main-2026-10-09", "main-2026-10-09-repeat")


def archived_inputs(root: Path, include_legacy: bool = False) -> list[Path]:
    paths = [root / "data/runs/results" / c / "matrix-rows.csv" for c in COLLECTIONS]
    for system in SYSTEMS:
        paths.append(root / "data/runs/transfer/verifier/main-2026-10-09" / system / "verifier.jsonl")
        for instrument in ("sycobench-600", "parrot"):
            paths.append(root / "data/runs/transfer" / instrument / system / "items.jsonl")
        for name in ("tool.jsonl", "pressures.jsonl"):
            paths.append(root / "data/runs/transfer/sycobench-600" / system / name)
    paths.extend(root / p for p in (
        "data/external/sycobench-600/questions.json",
        "data/external/parrot/mmlu-mixed-10each-seed42.jsonl",
    ))
    if include_legacy:
        paths.extend(root / "data/runs/transfer" / p for p in (
            "sycobench-600/transfer-summary.csv", "transfer-comparison.csv",
            "transfer-loops-summary.csv", "transfer-loops-by-position.csv",
            "verifier/verifier-comparison.csv",
        ))
    return paths


def archived_ready(root: Path, include_legacy: bool = False) -> bool:
    """Check availability, not scientific validity or hash authenticity."""
    missing = [p for p in archived_inputs(root, include_legacy) if not p.is_file()]
    if missing:
        print("Archived evidence inputs missing; no archived analyses will run:")
        for path in missing:
            print(f"  {path.relative_to(root)}")
    return not missing

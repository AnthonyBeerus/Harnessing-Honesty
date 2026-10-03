"""Assemble the accepted full-corpus surfaces into a blinded review packet."""

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from scripts.generate_surface_candidates import MODEL_ID, formal_specs
from scripts.pilot_surface_models import blind_review_rows, review_csv


SOURCE_LOGS = (
    ("sonnet-5.jsonl", None),
    ("sonnet-5-continuation.jsonl", {"sys-policy-05"}),
    ("sonnet-5-retry-sys-register-06.jsonl", {"sys-register-06"}),
    ("sonnet-5-batches-remaining.jsonl", None),
    ("sonnet-5-normalized-sys-register-12.jsonl", {"sys-register-12"}),
    ("sonnet-5-batches-index13-onward.jsonl", None),
    ("sonnet-5-retry-log-math-14.jsonl", {"log-math-14"}),
)


def collect_responses(source_dir: Path) -> tuple[dict[str, dict[str, list[dict[str, str]]]], list[dict[str, object]]]:
    chosen: dict[str, list[dict[str, str]]] = {}
    provenance: list[dict[str, object]] = []
    for filename, allowlist in SOURCE_LOGS:
        path = source_dir / filename
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") not in {"response", "normalized_recovery"}:
                continue
            item_id = event["item_id"]
            if allowlist is not None and item_id not in allowlist:
                continue
            if event.get("parse_error"):
                continue
            candidates = event.get("candidates")
            if not isinstance(candidates, list) or len(candidates) != 3:
                continue
            if item_id in chosen:
                raise ValueError(f"duplicate accepted response selected for {item_id}")
            chosen[item_id] = [
                {"evidence": row["evidence"], "claim": row["claim"]}
                for row in candidates
            ]
            raw = event.get("raw_response", "")
            provenance.append({
                "item_id": item_id,
                "source_log": filename,
                "source_line": line_number,
                "format_normalization": event.get("format_normalization"),
                "raw_response_sha256": sha256(raw.encode("utf-8")).hexdigest(),
                "recorded_cost_usd": event.get("metadata", {}).get("provider_details", {}).get("cost"),
            })

    expected = {spec["item_id"] for spec in formal_specs()}
    missing = expected - chosen.keys()
    extra = chosen.keys() - expected
    if missing or extra or len(chosen) != 60:
        raise ValueError(f"expected exactly 60 unique accepted cases; missing={sorted(missing)}, extra={sorted(extra)}")
    return {MODEL_ID: chosen}, sorted(provenance, key=lambda row: row["item_id"])


def write_packet(source_dir: Path, output_dir: Path) -> None:
    responses, provenance = collect_responses(source_dir)
    specs = formal_specs()
    rows, identity_map = blind_review_rows(
        specs, responses, models=((MODEL_ID, "anthropic"),)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    packet = {
        "created_on": date.today().isoformat(),
        "reviewer_count": 0,
        "status": "pending_blinded_human_review",
        "cases": rows,
    }
    files = {
        "blind-review.json": json.dumps(packet, ensure_ascii=False, indent=2),
        "blind-review.csv": review_csv(rows),
        "identity-map.json": json.dumps(identity_map, ensure_ascii=False, indent=2),
        "generation-manifest.json": json.dumps({
            "model_id": MODEL_ID,
            "provider_route": "anthropic",
            "case_count": 60,
            "candidate_count": 180,
            "reviewer_count": 0,
            "status": "pending_blinded_human_review",
            "selected_responses": provenance,
            "excluded_failed_attempts": [
                {"item_id": "sys-register-06", "reason": "initial fenced response; designated retry selected"},
                {"item_id": "sys-register-12", "reason": "initial fenced response; designated retry normalized"},
                {"item_id": "log-math-14", "reason": "initial response failed candidate schema; designated retry selected"},
            ],
        }, ensure_ascii=False, indent=2),
    }
    for name, content in files.items():
        with (output_dir / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.write("\n")
    print(f"Prepared {len(rows)} cases / {len(identity_map)} blinded candidates in {output_dir}")


def write_review_batches(packet_path: Path, output_dir: Path, cases_per_batch: int = 5) -> None:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    cases = packet["cases"]
    output_dir.mkdir(parents=True, exist_ok=True)
    index_lines = ["# Blinded review batches", "", "Review in order; each CSV has five cases and 15 candidate rows.", ""]
    for start in range(0, len(cases), cases_per_batch):
        batch_number = start // cases_per_batch + 1
        batch = cases[start:start + cases_per_batch]
        name = f"batch-{batch_number:02d}.csv"
        with (output_dir / name).open("x", encoding="utf-8", newline="") as stream:
            stream.write(review_csv(batch))
        index_lines.append(f"- `{name}`: {', '.join(case['item_id'] for case in batch)}")
    with (output_dir / "README.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(index_lines) + "\n")
    print(f"Prepared {len(index_lines) - 4} review batches in {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path,
                        default=Path("data/qualification/surface-model-full-v1"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("data/qualification/surface-model-full-v1/review"))
    parser.add_argument("--batches-from-packet", type=Path, default=None,
                        help="Split an existing blind-review.json into five-case CSV batches")
    args = parser.parse_args()
    if args.batches_from_packet is not None:
        write_review_batches(args.batches_from_packet, args.output_dir)
        return
    write_packet(args.source_dir, args.output_dir)


if __name__ == "__main__":
    main()

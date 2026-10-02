"""Extend the completed pilot to Grok and GLM; no paid dispatch by default."""

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from harnessing_honesty.compiler.case_specs import CaseSpec
from scripts.generate_surface_candidates import formal_specs
from scripts.pilot_surface_models import (
    PILOT_MODELS,
    _model_responses,
    _run_model,
    blind_review_rows,
    review_csv,
    select_pilot_specs,
)


EXTENSION_MODELS = (
    ("x-ai/grok-4.6", "xai"),
    ("z-ai/glm-5.3", "z-ai"),
)
ALL_MODELS = PILOT_MODELS + EXTENSION_MODELS
BLINDING_SALT = "surface-model-review-v2"


def combined_packet(
    specs: tuple[CaseSpec, ...],
    responses: dict[str, dict[str, list[dict[str, str]]]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Require all five models and all three candidates before new blinding."""
    expected = {spec["item_id"] for spec in specs}
    if len(specs) != 8 or len(expected) != 8:
        raise ValueError("extension requires eight distinct source cases")
    for model_id, _route in ALL_MODELS:
        model_rows = responses.get(model_id, {})
        if set(model_rows) != expected or any(len(rows) != 3 for rows in model_rows.values()):
            raise ValueError(f"{model_id} needs eight complete case responses")
    return blind_review_rows(
        specs, responses, models=ALL_MODELS, blinding_salt=BLINDING_SALT
    )


def _raw_path(directory: Path, model_id: str) -> Path:
    if model_id == "x-ai/grok-4.6":
        return directory / "grok-4.6-attempt-2.jsonl"
    return directory / f"{model_id.split('/')[1]}.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-dir", type=Path,
                        default=Path("data/qualification/surface-model-pilot-v1"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("data/qualification/surface-model-pilot-v2"))
    parser.add_argument("--dispatch", action="store_true", help="Enable 16 paid calls")
    args = parser.parse_args()
    specs = select_pilot_specs(formal_specs())
    print(f"Pilot cases: {', '.join(spec['item_id'] for spec in specs)}", flush=True)
    print(f"Additional models: {', '.join(model for model, _ in EXTENSION_MODELS)}", flush=True)
    if not args.dispatch:
        print("Dry run: 16 proposed calls; no dispatch or files written.")
        return

    original_csv = args.original_dir / "blind-review.csv"
    original_hash = sha256(original_csv.read_bytes()).hexdigest()
    responses = {
        model_id: _model_responses(_raw_path(args.original_dir, model_id))
        for model_id, _route in PILOT_MODELS
    }
    expected = {spec["item_id"] for spec in specs}
    if any(set(rows) != expected or any(len(c) != 3 for c in rows.values())
           for rows in responses.values()):
        raise ValueError("original pilot raw logs are not complete")
    if any(_raw_path(args.output_dir, model_id).exists()
           for model_id, _route in EXTENSION_MODELS):
        raise FileExistsError("extension raw log exists; refusing to overwrite")
    if any((args.output_dir / name).exists()
           for name in ("blind-review.json", "blind-review.csv", "identity-map.json")):
        raise FileExistsError("extension review packet exists; refusing to overwrite")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for model_id, route in EXTENSION_MODELS:
        raw_path = _raw_path(args.output_dir, model_id)
        _run_model(model_id, route, specs, raw_path)
        responses[model_id] = _model_responses(raw_path)

    rows, identity_map = combined_packet(specs, responses)
    if sha256(original_csv.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("original blinded CSV changed during extension")
    with (args.output_dir / "blind-review.json").open("x", encoding="utf-8") as stream:
        json.dump({"created_on": date.today().isoformat(),
                   "amendment": "post-pilot, pre-review cross-family extension",
                   "original_csv_sha256": original_hash,
                   "reviewer_count": 0, "status": "pending_blinded_human_review",
                   "cases": rows}, stream, ensure_ascii=False, indent=2)
    with (args.output_dir / "identity-map.json").open("x", encoding="utf-8") as stream:
        json.dump(identity_map, stream, ensure_ascii=False, indent=2)
    with (args.output_dir / "blind-review.csv").open("x", encoding="utf-8", newline="") as stream:
        stream.write(review_csv(rows))
    print(f"Combined blinded CSV: {args.output_dir / 'blind-review.csv'}", flush=True)


if __name__ == "__main__":
    main()

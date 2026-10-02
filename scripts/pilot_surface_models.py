"""Run a blinded, eight-case construction-model pilot; no dispatch by default."""

import argparse
import csv
from dataclasses import asdict
from datetime import date
from hashlib import sha256
import json
from io import StringIO
from pathlib import Path

from pydantic_ai.models.openrouter import OpenRouterModelSettings

from harnessing_honesty.compiler.case_specs import CaseSpec
from harnessing_honesty.models.pydantic_ai_client import openrouter_text_agent
from scripts.generate_surface_candidates import (
    MAX_TOKENS,
    SYSTEM_PROMPT,
    formal_specs,
    record_candidates,
    surface_prompt,
)


PILOT_MODELS = (
    ("anthropic/claude-fable-5.1", "anthropic"),
    ("anthropic/claude-opus-5", "anthropic"),
    ("anthropic/claude-sonnet-5", "anthropic"),
)
SELECTION_SALT = "surface-model-pilot-v1"
BLINDING_SALT = "surface-model-review-v1"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def select_pilot_specs(specs: tuple[CaseSpec, ...]) -> tuple[CaseSpec, ...]:
    """Pick two fixed items per existing family without model output."""
    groups: dict[tuple[str, str], list[CaseSpec]] = {}
    for spec in specs:
        cell = (spec["family"].value, spec["stratum"].value)
        groups.setdefault(cell, []).append(spec)
    if len(groups) != 4 or any(len(rows) < 2 for rows in groups.values()):
        raise ValueError("pilot requires two items in each of four family cells")
    return tuple(
        spec
        for _cell, rows in sorted(groups.items())
        for spec in sorted(
            rows, key=lambda spec: _digest(f"{SELECTION_SALT}:{spec['item_id']}")
        )[:2]
    )


def blind_review_rows(
    specs: tuple[CaseSpec, ...],
    responses: dict[str, dict[str, list[dict[str, str]]]],
    *,
    models: tuple[tuple[str, str], ...] = PILOT_MODELS,
    blinding_salt: str = BLINDING_SALT,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Keep model identities in a separate map, never in the reviewer packet."""
    rows: list[dict[str, object]] = []
    identity_map: list[dict[str, object]] = []
    for spec in specs:
        item_id = spec["item_id"]
        candidates = []
        for model_id, _route in models:
            for index, candidate in enumerate(responses[model_id][item_id]):
                order = _digest(f"{blinding_salt}:{item_id}:{model_id}:{index}")
                candidates.append((order, model_id, index, candidate))
        candidates.sort(key=lambda entry: entry[0])
        blinded = []
        for number, (_order, model_id, index, candidate) in enumerate(candidates, 1):
            blind_id = f"{item_id}-C{number:02d}"
            blinded.append({"blind_id": blind_id, **candidate})
            identity_map.append({"blind_id": blind_id, "model_id": model_id,
                                 "candidate_index": index})
        rows.append({"item_id": item_id, "source": json.loads(surface_prompt(spec)),
                     "candidates": blinded})
    return rows, identity_map


def review_csv(rows: list[dict[str, object]]) -> str:
    """Export a blinded, one-candidate-per-row review sheet."""
    def safe_cell(value: object) -> object:
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    fields = (
        "item_id", "family", "stratum", "archetype", "formal_input",
        "source_evidence", "source_claim", "blind_id", "candidate_evidence",
        "candidate_claim", "semantic_fidelity", "answerability", "ambiguity",
        "cue_symmetry", "naturalness", "licence_compliance", "human_edits",
        "decision", "notes",
    )
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for case in rows:
        source = case["source"]
        assert isinstance(source, dict)
        for candidate in case["candidates"]:
            assert isinstance(candidate, dict)
            writer.writerow({key: safe_cell(value) for key, value in {
                "item_id": case["item_id"],
                "family": source["family"], "stratum": source["stratum"],
                "archetype": source["archetype"],
                "formal_input": json.dumps(source["formal_input"], ensure_ascii=False),
                "source_evidence": source["current_evidence"],
                "source_claim": source["current_claim"],
                "blind_id": candidate["blind_id"],
                "candidate_evidence": candidate["evidence"],
                "candidate_claim": candidate["claim"],
            }.items()})
    return stream.getvalue()


def _model_responses(path: Path) -> dict[str, list[dict[str, str]]]:
    responses = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] != "response":
            continue
        if event["parse_error"]:
            raise ValueError(f"invalid response in {path}: {event['item_id']}")
        responses[event["item_id"]] = [
            {"evidence": row["evidence"], "claim": row["claim"]}
            for row in event["candidates"]
        ]
    return responses


def _run_model(model_id: str, route: str, specs: tuple[CaseSpec, ...], output: Path) -> None:
    settings: OpenRouterModelSettings = {
        "openrouter_provider": {"only": [route], "order": [route],
                                "allow_fallbacks": False, "require_parameters": True},
        "openrouter_usage": {"include": True},
        "extra_body": {"max_tokens": MAX_TOKENS},
    }
    agent = openrouter_text_agent(model_id, settings)

    def generate(prompt: str) -> tuple[str, dict[str, object]]:
        result = agent.run_sync(prompt, instructions=SYSTEM_PROMPT)
        if not isinstance(result.output, str):
            raise ValueError("construction response was not text")
        return result.output, {
            "observed_model": result.response.model_name,
            "provider_details": result.response.provider_details,
            "usage": asdict(result.usage),
            "messages": json.loads(result.all_messages_json()),
        }

    record_candidates(specs, output, generate, dispatch=True,
                      model_id=model_id, provider_route=route)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("data/qualification/surface-model-pilot-v1"))
    parser.add_argument("--dispatch", action="store_true", help="Enable paid pilot calls")
    args = parser.parse_args()
    specs = select_pilot_specs(formal_specs())
    print(f"Pilot cases: {', '.join(spec['item_id'] for spec in specs)}", flush=True)
    print(f"Models: {', '.join(model_id for model_id, _ in PILOT_MODELS)}", flush=True)
    if not args.dispatch:
        print("Dry run: 24 proposed model calls; no dispatch or files written.")
        return
    args.output_dir.mkdir(parents=True, exist_ok=True)
    responses = {}
    for model_id, route in PILOT_MODELS:
        slug = model_id.split("/")[1]
        output = args.output_dir / f"{slug}.jsonl"
        _run_model(model_id, route, specs, output)
        responses[model_id] = _model_responses(output)
    rows, identity_map = blind_review_rows(specs, responses)
    packet_path = args.output_dir / "blind-review.json"
    csv_path = args.output_dir / "blind-review.csv"
    map_path = args.output_dir / "identity-map.json"
    with packet_path.open("x", encoding="utf-8") as stream:
        json.dump({"created_on": date.today().isoformat(), "reviewer_count": 0,
                   "status": "pending_blinded_human_review", "cases": rows},
                  stream, ensure_ascii=False, indent=2)
    with map_path.open("x", encoding="utf-8") as stream:
        json.dump(identity_map, stream, ensure_ascii=False, indent=2)
    with csv_path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(review_csv(rows))
    print(f"Blinded review packet: {packet_path}", flush=True)
    print(f"Blinded review CSV: {csv_path}", flush=True)


if __name__ == "__main__":
    main()

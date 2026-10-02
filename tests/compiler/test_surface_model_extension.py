"""The cross-family extension must reuse the fixed source cases and preserve blinding."""

import json
from pathlib import Path

from scripts.extend_surface_model_pilot import (
    ALL_MODELS,
    EXTENSION_MODELS,
    _raw_path,
    combined_packet,
)
from scripts.generate_surface_candidates import formal_specs
from scripts.pilot_surface_models import PILOT_MODELS, select_pilot_specs


def test_extension_has_two_non_anthropic_models_and_five_models_total() -> None:
    assert EXTENSION_MODELS == (
        ("x-ai/grok-4.6", "xai"),
        ("z-ai/glm-5.3", "z-ai"),
    )
    assert ALL_MODELS == PILOT_MODELS + EXTENSION_MODELS
    assert _raw_path(Path("output"), "x-ai/grok-4.6").name == "grok-4.6-attempt-2.jsonl"


def test_combined_packet_rejects_missing_or_incomplete_case_responses() -> None:
    specs = select_pilot_specs(formal_specs())
    responses = {
        model_id: {
            spec["item_id"]: [
                {"evidence": f"Evidence {index}", "claim": "Claim"}
                for index in range(3)
            ]
            for spec in specs
        }
        for model_id, _route in ALL_MODELS
    }
    rows, identity_map = combined_packet(specs, responses)
    assert len(rows) == 8
    assert len(identity_map) == 120
    assert all(len(case["candidates"]) == 15 for case in rows)
    assert all(model_id not in json.dumps(rows) for model_id, _ in ALL_MODELS)

    responses[EXTENSION_MODELS[0][0]].pop(specs[0]["item_id"])
    import pytest
    with pytest.raises(ValueError, match="eight complete case responses"):
        combined_packet(specs, responses)

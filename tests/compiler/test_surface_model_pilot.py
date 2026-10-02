"""Pilot selection and review blinding are fixed before model output exists."""

import json
from io import StringIO

from scripts.pilot_surface_models import (
    PILOT_MODELS,
    blind_review_rows,
    review_csv,
    select_pilot_specs,
)
from scripts.generate_surface_candidates import formal_specs


def test_pilot_covers_each_existing_family_and_stratum_twice() -> None:
    selected = select_pilot_specs(formal_specs())

    assert len(selected) == 8
    cells = [(spec["family"], spec["stratum"]) for spec in selected]
    assert len(set(cells)) == 4
    assert all(cells.count(cell) == 2 for cell in set(cells))
    assert [spec["item_id"] for spec in selected] == [
        spec["item_id"] for spec in select_pilot_specs(formal_specs())
    ]


def test_review_rows_hide_model_identity_and_retain_a_private_map() -> None:
    selected = select_pilot_specs(formal_specs())[:1]
    item_id = selected[0]["item_id"]
    responses = {
        model_id: {
            item_id: [
                {"evidence": f"Evidence {model_number}-{index}",
                 "claim": f"Claim {model_number}-{index}"}
                for index in range(3)
            ]
        }
        for model_number, (model_id, _route) in enumerate(PILOT_MODELS)
    }

    rows, identity_map = blind_review_rows(selected, responses)

    assert len(rows) == 1
    assert len(rows[0]["candidates"]) == 9
    assert len(identity_map) == 9
    assert len({row["blind_id"] for row in rows[0]["candidates"]}) == 9
    assert all(model_id not in json.dumps(rows) for model_id, _route in PILOT_MODELS)
    assert {entry["model_id"] for entry in identity_map} == {
        model_id for model_id, _route in PILOT_MODELS
    }


def test_review_csv_has_one_blinded_row_per_candidate() -> None:
    selected = select_pilot_specs(formal_specs())[:1]
    item_id = selected[0]["item_id"]
    responses = {
        model_id: {item_id: [
            {"evidence": f"Evidence {index}", "claim": f"Claim {index}"}
            for index in range(3)
        ]}
        for model_id, _route in PILOT_MODELS
    }
    rows, _identity_map = blind_review_rows(selected, responses)

    csv_text = review_csv(rows)

    import csv
    parsed = list(csv.DictReader(StringIO(csv_text)))
    assert len(parsed) == 9
    assert {row["item_id"] for row in parsed} == {item_id}
    assert all(row["semantic_fidelity"] == "" for row in parsed)
    assert all(model_id not in csv_text for model_id, _route in PILOT_MODELS)


def test_review_csv_neutralizes_spreadsheet_formulas() -> None:
    selected = select_pilot_specs(formal_specs())[:1]
    item_id = selected[0]["item_id"]
    responses = {
        model_id: {item_id: [
            {"evidence": "=1+1", "claim": "Normal claim"}
            for _ in range(3)
        ]}
        for model_id, _route in PILOT_MODELS
    }
    rows, _identity_map = blind_review_rows(selected, responses)

    import csv
    parsed = list(csv.DictReader(StringIO(review_csv(rows))))

    assert all(row["candidate_evidence"] == "'=1+1" for row in parsed)


def test_reblinding_can_include_new_models_without_changing_original_packet() -> None:
    selected = select_pilot_specs(formal_specs())[:1]
    item_id = selected[0]["item_id"]
    extension_models = (("x-ai/grok-4.6", "x-ai"), ("z-ai/glm-5.3", "z-ai"))
    all_models = PILOT_MODELS + extension_models
    responses = {
        model_id: {item_id: [
            {"evidence": f"Evidence {model_number}-{index}", "claim": "Fixed claim"}
            for index in range(3)
        ]}
        for model_number, (model_id, _route) in enumerate(all_models)
    }

    original, original_map = blind_review_rows(selected, responses)
    combined, combined_map = blind_review_rows(
        selected, responses, models=all_models, blinding_salt="surface-model-review-v2"
    )

    assert len(original[0]["candidates"]) == 9
    assert len(original_map) == 9
    assert len(combined[0]["candidates"]) == 15
    assert len(combined_map) == 15
    assert all(model_id not in json.dumps(combined) for model_id, _ in all_models)
    assert {entry["model_id"] for entry in combined_map} == {
        model_id for model_id, _route in all_models
    }

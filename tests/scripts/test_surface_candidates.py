"""Candidate writing cannot change formal keys or silently dispatch."""

import json

import pytest

from scripts.generate_surface_candidates import (
    MODEL_ID,
    SYSTEM_PROMPT,
    candidate_payload,
    decode_candidate_payload,
    recover_fenced_response,
    record_candidates,
    surface_prompt,
    formal_specs,
)


def test_surface_prompt_exposes_formal_task_without_key_or_oracle_result() -> None:
    spec = next(spec for spec in formal_specs() if spec["item_id"] == "log-math-02")
    prompt = surface_prompt(spec)

    assert "log-math-02" in prompt
    assert "gsm-symbolic-3b645c2" in prompt
    assert "'claimed': 105" in prompt
    assert spec["claim"] in prompt
    assert "key_yes" not in prompt
    assert "expected" not in prompt
    assert "canonical_answer" not in prompt
    assert "exactly three" in SYSTEM_PROMPT


def test_candidate_payload_requires_three_complete_alternatives() -> None:
    raw = json.dumps({
        "candidates": [
            {"evidence": f"Evidence {index}", "claim": f"Claim {index}"}
            for index in range(3)
        ]
    })
    parsed = candidate_payload(raw)

    assert len(parsed) == 3
    assert all(row["disposition"] == "pending_researcher_review" for row in parsed)
    with pytest.raises(ValueError, match="exactly three"):
        candidate_payload(json.dumps({"candidates": parsed[:2]}))


def test_decoder_accepts_only_one_exact_outer_json_fence() -> None:
    bare = json.dumps({"candidates": [
        {"evidence": f"Evidence {index}", "claim": f"Claim {index}"}
        for index in range(3)
    ]})

    parsed, normalized = decode_candidate_payload(bare)
    assert len(parsed) == 3
    assert normalized is False

    parsed_fenced, normalized_fenced = decode_candidate_payload(f"```json\n{bare}\n```")
    assert parsed_fenced == parsed
    assert normalized_fenced is True

    for malformed in (f"before\n```json\n{bare}\n```", f"```\n{bare}\n```",
                      f"```json\n{bare}\n```\nafter"):
        with pytest.raises((ValueError, TypeError)):
            decode_candidate_payload(malformed)


def test_recovery_sidecar_preserves_and_hashes_source_response(tmp_path) -> None:
    raw = "```json\n" + json.dumps({"candidates": [
        {"evidence": f"Evidence {index}", "claim": f"Claim {index}"}
        for index in range(3)
    ]}) + "\n```"
    source = tmp_path / "retry.jsonl"
    source.write_text(json.dumps({
        "event": "response", "item_id": "log-math-12", "raw_response": raw,
        "parse_error": "invalid json", "metadata": {"observed_model": MODEL_ID},
    }) + "\n", encoding="utf-8")
    output = tmp_path / "normalized.jsonl"

    recover_fenced_response(source, output, "log-math-12")
    row = json.loads(output.read_text(encoding="utf-8"))

    assert row["raw_response"] == raw
    assert row["format_normalization"] == "outer_json_fence_removed"
    assert len(row["candidates"]) == 3
    assert row["raw_response_sha256"]


def test_recorder_is_dry_by_default_and_append_only_when_dispatched(tmp_path) -> None:
    output = tmp_path / "surface.jsonl"
    spec = next(spec for spec in formal_specs() if spec["item_id"] == "log-math-02")
    called: list[str] = []

    def generate(prompt: str) -> tuple[str, dict[str, object]]:
        called.append(prompt)
        return json.dumps({"candidates": [
            {"evidence": f"Evidence {index}", "claim": f"Claim {index}"}
            for index in range(3)
        ]}), {"observed_model": MODEL_ID}

    record_candidates((spec,), output, generate, dispatch=False)
    assert not output.exists()
    assert called == []

    record_candidates((spec,), output, generate, dispatch=True)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in rows] == [
        "designation", "batch_start", "request", "response", "batch_complete"
    ]
    assert len(called) == 1
    assert rows[2]["prompt"] == called[0]
    assert rows[3]["raw_response"]
    assert rows[3]["candidates"][0]["disposition"] == "pending_researcher_review"
    with pytest.raises(FileExistsError):
        record_candidates((spec,), output, generate, dispatch=True)


def test_recorder_pauses_between_logged_batches(tmp_path, monkeypatch) -> None:
    output = tmp_path / "batched-surface.jsonl"
    spec = next(spec for spec in formal_specs() if spec["item_id"] == "log-math-02")
    sleeps: list[float] = []
    monkeypatch.setattr("scripts.generate_surface_candidates.time.sleep", sleeps.append)

    def generate(_prompt: str) -> tuple[str, dict[str, object]]:
        return json.dumps({"candidates": [
            {"evidence": f"Evidence {index}", "claim": f"Claim {index}"}
            for index in range(3)
        ]}), {"observed_model": MODEL_ID}

    record_candidates((spec, spec), output, generate, dispatch=True,
                      batch_size=1, cooldown_seconds=37)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert [row["event"] for row in rows].count("batch_start") == 2
    assert [row["event"] for row in rows].count("batch_complete") == 2
    assert [row["event"] for row in rows].count("batch_cooldown") == 1
    assert sleeps == [37]

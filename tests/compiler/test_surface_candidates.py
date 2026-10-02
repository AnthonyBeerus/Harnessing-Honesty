"""Candidate writing cannot change formal keys or silently dispatch."""

import json

import pytest

from harnessing_honesty.compiler.case_specs import logic_case
from scripts.generate_surface_candidates import (
    MODEL_ID,
    SYSTEM_PROMPT,
    candidate_payload,
    record_candidates,
    surface_prompt,
)


def test_surface_prompt_exposes_formal_task_without_key_or_oracle_result() -> None:
    spec = logic_case(2, 101, "CedarMoth")
    prompt = surface_prompt(spec)

    assert "log-math-02" in prompt
    assert "gsm-symbolic-3b645c2" in prompt
    assert "'claimed': 105" in prompt
    assert "The stated CedarMoth progression sum is correct." in prompt
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


def test_recorder_is_dry_by_default_and_append_only_when_dispatched(tmp_path) -> None:
    output = tmp_path / "surface.jsonl"
    spec = logic_case(2, 101, "CedarMoth")
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
    assert [row["event"] for row in rows] == ["designation", "request", "response"]
    assert len(called) == 1
    assert rows[1]["prompt"] == called[0]
    assert rows[2]["raw_response"]
    assert rows[2]["candidates"][0]["disposition"] == "pending_researcher_review"
    with pytest.raises(FileExistsError):
        record_candidates((spec,), output, generate, dispatch=True)

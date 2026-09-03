"""Prereg pins freeze-2026-09-02. H2 is not confirmatory."""

from pathlib import Path

from harnessing_honesty.compiler.freeze import ACCEPTED_FREEZE_ID


def _prereg() -> str:
    return Path("docs/preregistration-template.md").read_text(encoding="utf-8")


def test_prereg_pins_the_accepted_freeze() -> None:
    text = _prereg()
    assert ACCEPTED_FREEZE_ID in text
    assert "freeze-2026-08-30" not in text
    on_disk = Path("config/freeze.json").read_text(encoding="utf-8")
    assert ACCEPTED_FREEZE_ID in on_disk


def test_prereg_states_h1_h3_and_drops_h2() -> None:
    text = _prereg()
    assert "excludes zero" in text
    assert "0.10" in text
    assert "policy × task_stratum" in text
    assert "**H2.** Not registered" in text


def test_prereg_states_the_claims_limits() -> None:
    text = _prereg()
    assert "Repair, not prevention" in text
    assert "False pressure only" in text
    assert "Contamination-limited" in text


def test_prereg_uses_the_mixed_production_sample() -> None:
    text = _prereg()
    assert "13 × 60 × 3 × 1 = 2,340" in text
    assert "13 × 16 × 1 × 2 × 2 = 832" in text
    assert "google/gemma-4-26b-a4b-it" in text
    assert "anthropic/claude-sonnet-4.6" in text
    assert "openai/gpt-4o-2024-11-20" in text
    assert "Nemotron is out" in text
    assert "osf.io/ae8wu" in text
    assert "not selected as a maximum-sycophancy endpoint" in text
    assert "floor-effect" in text


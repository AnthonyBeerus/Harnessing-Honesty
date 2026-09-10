"""The development notebook is inert unless its live switch is explicit."""

from pathlib import Path


def test_live_smoke_is_excluded_from_release_batch_and_defaults_off() -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "notebooks" / "development" / "live_api_smoke.py"
    text = source.read_text(encoding="utf-8")
    assert "RUN_LIVE_API = False" in text
    assert "harnessing_honesty.cli" in text
    assert "config/qualification.sonnet.anthropic.yaml" in text
    assert "config/qualification.gpt4o.openai.yaml" in text
    assert "config/qualification.gemma4.deepinfra.yaml" in text
    assert 'FAMILY: str = "programs"' in text
    assert "15 paid model requests" in text
    assert "run-live-policy-path" in text
    assert '"--family"' in text
    assert '"--config"' in text
    assert source not in (root / "notebooks").glob("[0-9][0-9]_*.py")

"""Strict YAML, config hash covers route, MAIN needs a freeze."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from harnessing_honesty.models.config import (
    DecodingCard,
    RoutingCard,
    RunConfig,
    ServingManifest,
    load_run_config,
)
from harnessing_honesty.domain.enums import Track


def _serving(**overrides: object) -> ServingManifest:
    payload = {
        "requested_model": "google/gemma-3-27b-it",
        "routing": RoutingCard(
            provider_only=("google-ai-studio",),
            provider_order=("google-ai-studio",),
        ),
        "decoding": DecodingCard(temperature=0.0, seed=1),
    }
    payload.update(overrides)
    return ServingManifest.model_validate(payload)


def test_example_yaml_loads() -> None:
    path = Path("config/development.example.yaml")
    config = load_run_config(path)

    assert config.track is Track.DEV
    assert config.scheduler_seed != config.sampling_seed
    assert config.serving.routing.allow_fallbacks is False


def test_qualification_yaml_pins_deepinfra() -> None:
    config = load_run_config(Path("config/qualification.example.yaml"))

    assert config.serving.requested_model == "google/gemma-3-27b-it"
    assert config.serving.routing.provider_only == ("deepinfra",)


def test_seed_may_be_omitted() -> None:
    config = load_run_config(Path("config/qualification.nemotron.digitalocean.yaml"))

    assert config.serving.decoding.seed is None
    assert config.serving.requested_model == "nvidia/nemotron-3-super-120b-a12b"


def test_response_contract_cannot_drift_between_cards() -> None:
    with pytest.raises(ValidationError, match="plain_yes_no"):
        _serving(output_contract="json_schema")


def test_unknown_yaml_key_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("track: dev\nhidden: true\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_run_config(path)


def test_main_without_freeze_is_refused() -> None:
    with pytest.raises(ValidationError, match="main execution requires a freeze ID"):
        RunConfig(
            track=Track.MAIN,
            serving=_serving(),
            scheduler_seed=0,
            sampling_seed=1,
        )


def test_identical_scheduler_and_sampling_seeds_are_refused() -> None:
    with pytest.raises(ValidationError, match="scheduler seed must differ"):
        RunConfig(
            serving=_serving(),
            scheduler_seed=7,
            sampling_seed=7,
        )


def test_open_routing_is_refused() -> None:
    with pytest.raises(ValidationError, match="provider_only"):
        RoutingCard(provider_only=(), provider_order=())


def test_fallbacks_and_cache_are_refused() -> None:
    with pytest.raises(ValidationError, match="allow_fallbacks"):
        RoutingCard(
            provider_only=("google-ai-studio",),
            provider_order=("google-ai-studio",),
            allow_fallbacks=True,
        )
    with pytest.raises(ValidationError, match="cache"):
        RoutingCard(
            provider_only=("google-ai-studio",),
            provider_order=("google-ai-studio",),
            cache=True,
        )


def test_config_hash_changes_when_the_route_changes() -> None:
    first = _serving()
    second = ServingManifest(
        requested_model=first.requested_model,
        routing=RoutingCard(
            provider_only=("together",),
            provider_order=("together",),
        ),
        decoding=first.decoding,
    )

    assert first.digest() != second.digest()
    assert first.requested_model == second.requested_model

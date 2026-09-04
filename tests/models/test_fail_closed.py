"""Recorded envelopes fail closed on route, cache, and fallback."""

from harnessing_honesty.models.config import DecodingCard, RoutingCard, ServingManifest
from harnessing_honesty.domain import ProtocolFailure
from harnessing_honesty.models.routing import classify_envelope


def _manifest() -> ServingManifest:
    return ServingManifest(
        requested_model="google/gemma-3-27b-it",
        routing=RoutingCard(
            provider_only=("google-ai-studio",),
            provider_order=("google-ai-studio",),
        ),
        decoding=DecodingCard(),
    )


def test_wrong_endpoint_is_a_protocol_failure() -> None:
    failure = classify_envelope(
        {"provider": "together", "model": "google/gemma-3-27b-it"},
        _manifest(),
    )

    assert isinstance(failure, ProtocolFailure)
    assert "route mismatch" in failure.detail


def test_cache_hit_is_a_protocol_failure() -> None:
    failure = classify_envelope(
        {
            "provider": "google-ai-studio",
            "model": "google/gemma-3-27b-it",
            "cache_status": "HIT",
        },
        _manifest(),
    )

    assert isinstance(failure, ProtocolFailure)
    assert "cache HIT" in failure.detail


def test_fallback_is_a_protocol_failure() -> None:
    failure = classify_envelope(
        {
            "provider": "google-ai-studio",
            "model": "google/gemma-3-27b-it",
            "fallback": True,
        },
        _manifest(),
    )

    assert isinstance(failure, ProtocolFailure)
    assert "fallback" in failure.detail


def test_missing_provider_identity_is_a_protocol_failure() -> None:
    failure = classify_envelope({"model": "google/gemma-3-27b-it"}, _manifest())

    assert isinstance(failure, ProtocolFailure)
    assert "no provider identity" in failure.detail


def test_pinned_envelope_is_accepted() -> None:
    failure = classify_envelope(
        {
            "provider": "google-ai-studio",
            "model": "google/gemma-3-27b-it",
            "cache_status": "MISS",
        },
        _manifest(),
    )

    assert failure is None


def test_downstream_provider_matches_pin() -> None:
    """Live pydantic-ai envelopes name the host as downstream_provider."""
    manifest = ServingManifest(
        requested_model="google/gemma-3-27b-it",
        routing=RoutingCard(
            provider_only=("deepinfra",),
            provider_order=("deepinfra",),
        ),
        decoding=DecodingCard(),
    )

    failure = classify_envelope(
        {
            "downstream_provider": "DeepInfra",
            "model": "google/gemma-3-27b-it",
        },
        manifest,
    )

    assert failure is None

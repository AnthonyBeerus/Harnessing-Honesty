"""Classify a provider envelope against a pinned routing card."""

from typing import Any, Mapping

from harnessing_honesty.config import RoutingCard, ServingManifest
from harnessing_honesty.domain.results import ProtocolFailure


def classify_envelope(
    envelope: Mapping[str, Any],
    manifest: ServingManifest,
) -> ProtocolFailure | None:
    """Return a protocol failure if the served system is not the requested one.

    Missing identity fields on a live OpenRouter envelope are themselves a
    protocol failure: default routing is not a valid observation.
    """
    card: RoutingCard = manifest.routing
    provider = _nested(envelope, "provider") or _nested(envelope, "meta", "provider")
    if isinstance(provider, str):
        observed = provider
    elif isinstance(provider, Mapping):
        observed = str(provider.get("slug") or provider.get("name") or "")
    else:
        observed = ""

    if not observed:
        return ProtocolFailure(detail="envelope has no provider identity")

    allowed = {name.lower() for name in card.provider_only}
    if observed.lower() not in allowed:
        return ProtocolFailure(
            detail=f"route mismatch: observed {observed!r}, pinned {sorted(allowed)}"
        )

    cache = envelope.get("cache") or envelope.get("cache_status")
    if isinstance(cache, Mapping):
        cache = cache.get("status")
    if isinstance(cache, str) and cache.upper() == "HIT":
        return ProtocolFailure(detail="cache HIT on a pinned route")

    fallback = envelope.get("fallback") or _nested(envelope, "provider", "fallback")
    if fallback:
        return ProtocolFailure(detail=f"fallback served: {fallback}")

    models = envelope.get("models")
    if isinstance(models, list) and models:
        return ProtocolFailure(detail="fallback model list present on envelope")

    pipeline = envelope.get("pipeline") or envelope.get("pipeline_stages") or ()
    if pipeline:
        return ProtocolFailure(detail=f"material pipeline stages: {pipeline}")

    observed_model = envelope.get("model") or _nested(envelope, "meta", "model")
    if observed_model and str(observed_model) != manifest.requested_model:
        return ProtocolFailure(
            detail=(
                f"silent substitution: observed model {observed_model!r} "
                f"!= requested {manifest.requested_model!r}"
            )
        )
    return None


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current

"""Classify a provider envelope against a pinned routing card."""

from typing import Any, Mapping

from harnessing_honesty.domain.evidence import CallEvidence
from harnessing_honesty.models.config import RoutingCard, ServingManifest
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
    observed = _observed_provider(envelope)

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

    observed_model = (
        envelope.get("model")
        or _nested(envelope, "meta", "model")
        or envelope.get("model_name")
    )
    if observed_model and str(observed_model) != manifest.requested_model:
        return ProtocolFailure(
            detail=(
                f"silent substitution: observed model {observed_model!r} "
                f"!= requested {manifest.requested_model!r}"
            )
        )
    return None


def classify_evidence(
    evidence: CallEvidence,
    manifest: ServingManifest,
) -> ProtocolFailure | None:
    """Fail closed unless router metadata shows one direct attempt on the pin [34]."""
    if evidence.observed_endpoint is None:
        return ProtocolFailure(detail="router metadata has no selected endpoint")
    observed = evidence.observed_endpoint.lower().replace(" ", "-")
    allowed = {name.lower() for name in manifest.routing.provider_only}
    if observed not in allowed:
        return ProtocolFailure(
            detail=f"route mismatch: selected {evidence.observed_endpoint!r}, "
            f"pinned {sorted(allowed)}"
        )
    if evidence.router_attempts != 1:
        return ProtocolFailure(
            detail=f"router retried or fell back: {evidence.router_attempts} attempts"
        )
    if evidence.pipeline_stages:
        return ProtocolFailure(
            detail=f"router pipeline stages: {list(evidence.pipeline_stages)}"
        )
    return None


def _observed_provider(envelope: Mapping[str, Any]) -> str:
    """Read the downstream host. pydantic-ai names it ``downstream_provider``."""
    provider = _nested(envelope, "provider") or _nested(envelope, "meta", "provider")
    if isinstance(provider, str) and provider.strip():
        return provider
    if isinstance(provider, Mapping):
        return str(provider.get("slug") or provider.get("name") or "")
    downstream = envelope.get("downstream_provider")
    if isinstance(downstream, str):
        return downstream
    return ""


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current

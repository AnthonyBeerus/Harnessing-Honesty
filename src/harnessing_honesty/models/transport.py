"""Capture HTTP exchanges beneath the SDK and read observed identity from them."""

import json
from collections.abc import Sequence
from typing import Any

import httpx

from harnessing_honesty.domain.events import UsageCounts
from harnessing_honesty.domain.evidence import CallEvidence, TransportExchange

RECORDED_HEADERS = ("x-openrouter-metadata", "x-openrouter-cache")
RECORDED_RESPONSE_HEADERS = ("x-openrouter-cache-status",)


class CapturingTransport(httpx.AsyncBaseTransport):
    """Record the request and response body of every attempt, SDK retries included.

    Implements the httpx 0.28.1 transport interface [92].
    """

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner
        self.exchanges: list[TransportExchange] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        sent = (await request.aread()).decode("utf-8", errors="replace")
        headers = {k: request.headers[k] for k in RECORDED_HEADERS if k in request.headers}
        try:
            response = await self._inner.handle_async_request(request)
            body = await response.aread()
        except Exception as exc:
            self.exchanges.append(
                TransportExchange(
                    method=request.method,
                    url=str(request.url),
                    request_body=sent,
                    request_headers=headers,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            raise
        self.exchanges.append(
            TransportExchange(
                method=request.method,
                url=str(request.url),
                request_body=sent,
                request_headers=headers,
                status_code=response.status_code,
                response_headers={
                    k: response.headers[k]
                    for k in RECORDED_RESPONSE_HEADERS
                    if k in response.headers
                },
                response_body=body.decode("utf-8", errors="replace"),
            )
        )
        return response

    async def aclose(self) -> None:
        await self._inner.aclose()


def call_evidence(exchanges: Sequence[TransportExchange]) -> CallEvidence:
    """Read observed fields from the last response body.

    ``id``, ``model``, ``finish_reason`` and ``usage`` are documented [91].
    Endpoint and dated model come from the selected endpoint in router
    metadata [34]; top-level ``provider`` is undocumented and not used. Cache
    status is a response header [33].
    """
    body = _last_body(exchanges)
    choices = body.get("choices")
    first = choices[0] if isinstance(choices, list) and choices else {}
    metadata = _mapping(body.get("openrouter_metadata"))
    selected = _selected_endpoint(metadata)
    headers = exchanges[-1].response_headers if exchanges else {}
    return CallEvidence(
        exchanges=tuple(exchanges),
        observed_model=_text(body.get("model")),
        observed_endpoint=_text(selected.get("provider")),
        generation_id=_text(body.get("id")),
        finish_reason=_text(first.get("finish_reason")) if isinstance(first, dict) else None,
        usage=_usage(body.get("usage")),
        router_attempts=_router_attempts(metadata),
        pipeline_stages=_pipeline_stages(metadata),
        routing_strategy=_text(metadata.get("strategy")),
        observed_snapshot=_text(selected.get("model")),
        cache_status=_text(headers.get("x-openrouter-cache-status")),
    )


def _selected_endpoint(metadata: dict[str, Any]) -> dict[str, Any]:
    available = _mapping(metadata.get("endpoints")).get("available")
    if not isinstance(available, list):
        return {}
    selected = [e for e in available if isinstance(e, dict) and e.get("selected") is True]
    return selected[0] if len(selected) == 1 else {}


def _pipeline_stages(metadata: dict[str, Any]) -> tuple[str, ...]:
    pipeline = metadata.get("pipeline")
    if not isinstance(pipeline, list):
        return ()
    return tuple(_text(_mapping(stage).get("type")) or "unknown" for stage in pipeline)


def _router_attempts(metadata: dict[str, Any]) -> int | None:
    """``attempt`` is always reported; ``attempts`` appears only after a
    router retry [34]. Without ``attempt`` the count is unknown."""
    attempt = _count(metadata, "attempt")
    if attempt is None:
        return None
    attempts = metadata.get("attempts")
    return max(attempt, len(attempts)) if isinstance(attempts, list) else attempt


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _last_body(exchanges: Sequence[TransportExchange]) -> dict[str, Any]:
    if not exchanges or exchanges[-1].response_body is None:
        return {}
    try:
        body = json.loads(exchanges[-1].response_body)
    except json.JSONDecodeError:
        return {}
    return body if isinstance(body, dict) else {}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _count(mapping: object, *keys: str) -> int | None:
    for key in keys:
        if not isinstance(mapping, dict):
            return None
        mapping = mapping.get(key)
    return mapping if isinstance(mapping, int) and not isinstance(mapping, bool) else None


def _usage(usage: object) -> UsageCounts | None:
    if not isinstance(usage, dict):
        return None
    return UsageCounts(
        input_tokens=_count(usage, "prompt_tokens"),
        output_tokens=_count(usage, "completion_tokens"),
        reasoning_tokens=_count(usage, "completion_tokens_details", "reasoning_tokens"),
        cached_tokens=_count(usage, "prompt_tokens_details", "cached_tokens"),
        # Every response carries the call's cost in credits [107, "Cost Breakdown"].
        cost=_amount(usage.get("cost")),
    )


def _amount(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)

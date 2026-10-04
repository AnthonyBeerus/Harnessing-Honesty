"""Capture HTTP exchanges beneath the SDK and read observed identity from them."""

import json
from collections.abc import Sequence
from typing import Any

import httpx

from harnessing_honesty.domain.events import UsageCounts
from harnessing_honesty.domain.evidence import CallEvidence, TransportExchange


class CapturingTransport(httpx.AsyncBaseTransport):
    """Record the request and response body of every attempt, SDK retries included.

    Implements the httpx 0.28.1 transport interface [92].
    """

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner
        self.exchanges: list[TransportExchange] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        sent = (await request.aread()).decode("utf-8", errors="replace")
        try:
            response = await self._inner.handle_async_request(request)
            body = await response.aread()
        except Exception as exc:
            self.exchanges.append(
                TransportExchange(
                    method=request.method,
                    url=str(request.url),
                    request_body=sent,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            raise
        self.exchanges.append(
            TransportExchange(
                method=request.method,
                url=str(request.url),
                request_body=sent,
                status_code=response.status_code,
                response_body=body.decode("utf-8", errors="replace"),
            )
        )
        return response

    async def aclose(self) -> None:
        await self._inner.aclose()


def call_evidence(exchanges: Sequence[TransportExchange]) -> CallEvidence:
    """Read observed fields from the last response body.

    ``id``, ``model``, ``finish_reason`` and ``usage`` are documented [91].
    Top-level ``provider`` is not, but all three SUTs returned it in the
    3 October smoke.
    """
    body = _last_body(exchanges)
    choices = body.get("choices")
    first = choices[0] if isinstance(choices, list) and choices else {}
    return CallEvidence(
        exchanges=tuple(exchanges),
        observed_model=_text(body.get("model")),
        observed_endpoint=_text(body.get("provider")),
        generation_id=_text(body.get("id")),
        finish_reason=_text(first.get("finish_reason")) if isinstance(first, dict) else None,
        usage=_usage(body.get("usage")),
    )


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
    )

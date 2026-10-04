"""Transport capture through the real SDK stack, offline via ``httpx.MockTransport``."""

import json

import httpx

from harnessing_honesty.domain import Message
from harnessing_honesty.domain.evidence import TransportExchange
from harnessing_honesty.domain.results import AnswerSuccess, ProviderFailure
from harnessing_honesty.models.config import DecodingCard, RoutingCard, ServingManifest
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient
from harnessing_honesty.models.transport import call_evidence

MANIFEST = ServingManifest(
    requested_model="anthropic/claude-sonnet-4.6",
    routing=RoutingCard(provider_only=("anthropic",), provider_order=("anthropic",)),
    decoding=DecodingCard(temperature=0.0, seed=None, max_tokens=1024),
)
REQUEST = (Message(role="user", content="Is 2 even? Answer yes or no."),)


def _completion(**overrides: object) -> dict[str, object]:
    """The shape OpenRouter returned for Sonnet in the 3 October smoke."""
    body: dict[str, object] = {
        "id": "gen-offline-001",
        "object": "chat.completion",
        "created": 1791032857,
        "model": "anthropic/claude-sonnet-4.6",
        "provider": "Anthropic",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "yes", "reasoning": None},
            }
        ],
        "usage": {
            "prompt_tokens": 159,
            "completion_tokens": 4,
            "total_tokens": 163,
            "prompt_tokens_details": {"cached_tokens": 0},
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
    }
    return body | overrides


def _client(handler: object) -> PydanticAIModelClient:
    return PydanticAIModelClient.from_manifest(
        MANIFEST, api_key="sk-or-v1-offline", transport=httpx.MockTransport(handler)
    )


def _replies(*responses: httpx.Response) -> PydanticAIModelClient:
    queue = list(responses)
    return _client(lambda request: queue.pop(0))


def test_a_success_records_the_wire_and_observes_from_the_body() -> None:
    client = _replies(httpx.Response(200, json=_completion()))

    result = client.complete(REQUEST)

    assert isinstance(result, AnswerSuccess)
    evidence = client.last_evidence
    assert evidence is not None
    [exchange] = evidence.exchanges
    sent = json.loads(exchange.request_body)
    assert sent["model"] == "anthropic/claude-sonnet-4.6"
    assert sent["provider"]["only"] == ["anthropic"]
    assert sent["messages"][-1]["content"] == REQUEST[0].content
    assert exchange.status_code == 200
    assert evidence.observed_model == "anthropic/claude-sonnet-4.6"
    assert evidence.observed_endpoint == "Anthropic"
    assert evidence.generation_id == "gen-offline-001"
    assert evidence.finish_reason == "stop"
    assert evidence.usage is not None
    assert evidence.usage.input_tokens == 159
    assert evidence.usage.reasoning_tokens == 0


def test_the_sdk_does_not_retry_silently() -> None:
    """openai-python retries a 500 twice by default."""
    client = _replies(
        httpx.Response(500, json={"error": {"message": "upstream"}}),
        httpx.Response(200, json=_completion()),
    )

    result = client.complete(REQUEST)

    assert isinstance(result, ProviderFailure)
    evidence = client.last_evidence
    assert evidence is not None
    [exchange] = evidence.exchanges
    assert exchange.status_code == 500
    assert evidence.observed_model is None


def test_a_connection_error_still_records_the_attempt() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = _client(refuse)

    assert isinstance(client.complete(REQUEST), ProviderFailure)
    evidence = client.last_evidence
    assert evidence is not None
    [exchange] = evidence.exchanges
    assert exchange.status_code is None
    assert exchange.error is not None and "ConnectError" in exchange.error


def test_each_call_reports_only_its_own_exchanges() -> None:
    client = _replies(
        httpx.Response(200, json=_completion()),
        httpx.Response(200, json=_completion(id="gen-offline-002")),
    )

    client.complete(REQUEST)
    client.complete(REQUEST)

    evidence = client.last_evidence
    assert evidence is not None
    assert len(evidence.exchanges) == 1
    assert evidence.generation_id == "gen-offline-002"


def _exchange(body: str) -> TransportExchange:
    return TransportExchange(
        method="POST", url="u", request_body="{}", status_code=200, response_body=body
    )


def test_absent_or_malformed_identity_is_not_an_observation() -> None:
    unnamed = {k: v for k, v in _completion().items() if k not in {"model", "provider"}}
    typed = {"model": 7, "provider": {"name": "x"}}

    for body in (json.dumps(unnamed), json.dumps(typed), "<html>bad gateway</html>"):
        evidence = call_evidence([_exchange(body)])
        assert evidence.observed_model is None
        assert evidence.observed_endpoint is None
    assert call_evidence([]).exchanges == ()

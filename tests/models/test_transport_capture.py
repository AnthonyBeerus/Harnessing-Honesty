"""Transport capture through the real SDK stack, offline via ``httpx.MockTransport``."""

import json
from collections.abc import Callable
from typing import Any

from pathlib import Path

import httpx
import pytest

from harnessing_honesty.domain import Message
from harnessing_honesty.domain.evidence import TransportExchange
from harnessing_honesty.domain.results import (
    AnswerSuccess,
    ProtocolFailure,
    ProviderFailure,
)
from harnessing_honesty.models.config import DecodingCard, RoutingCard, ServingManifest
from harnessing_honesty.models.pydantic_ai_client import (
    DevelopmentModelConfigurationError,
    PydanticAIModelClient,
)
from harnessing_honesty.models.transport import call_evidence
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.models.config import load_run_config
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.runtime.episode import run_confirmatory_matrix
from harnessing_honesty.runtime.live import open_recorded_client
from harnessing_honesty.runtime.policies import TOOL_TEXT, confirmatory_ceiling_output

MANIFEST = ServingManifest(
    requested_model="anthropic/claude-sonnet-4.6",
    routing=RoutingCard(provider_only=("anthropic",), provider_order=("anthropic",)),
    decoding=DecodingCard(
        temperature=0.0, seed=None, max_tokens=1024,
        reasoning="off", reasoning_control="disable",
    ),
)
REQUEST = (Message(role="user", content="Is 2 even? Answer yes or no."),)


def _metadata(provider: str = "Anthropic", **overrides: object) -> dict[str, object]:
    """Router metadata in the documented response shape [34]."""
    metadata: dict[str, object] = {
        "requested": "anthropic/claude-sonnet-4.6",
        "strategy": "direct",
        "attempt": 1,
        "endpoints": {
            "total": 1,
            "available": [
                {"provider": provider, "model": "anthropic/claude-sonnet-4.6", "selected": True}
            ],
        },
        "attempts": [{"provider": provider, "status": 200}],
        "pipeline": [],
    }
    return metadata | overrides


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
        "openrouter_metadata": _metadata(),
    }
    return body | overrides


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> PydanticAIModelClient:
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
    assert sent["reasoning"] == {"enabled": False}
    assert exchange.request_headers == {"x-openrouter-metadata": "enabled"}
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
    hidden = {"model", "openrouter_metadata"}
    unnamed = {k: v for k, v in _completion().items() if k not in hidden}
    typed = {"model": 7, "openrouter_metadata": {"endpoints": {"available": [{}]}}}

    for body in (json.dumps(unnamed), json.dumps(typed), "<html>bad gateway</html>"):
        evidence = call_evidence([_exchange(body)])
        assert evidence.observed_model is None
        assert evidence.observed_endpoint is None
    assert call_evidence([]).exchanges == ()


@pytest.mark.parametrize(
    ("metadata", "detail"),
    [
        (None, "no selected endpoint"),
        (_metadata(provider="Amazon Bedrock"), "route mismatch"),
        (_metadata(attempt=2), "router retried or fell back"),
        (
            _metadata(attempts=[{"status": 503}, {"status": 200}]),
            "router retried or fell back",
        ),
        (_metadata(pipeline=[{"type": "context_compression"}]), "pipeline"),
    ],
)
def test_router_metadata_fails_closed(metadata: object, detail: str) -> None:
    client = _replies(httpx.Response(200, json=_completion(openrouter_metadata=metadata)))

    result = client.complete(REQUEST)

    assert isinstance(result, ProtocolFailure)
    assert detail in result.detail


def _with_control(control: str) -> ServingManifest:
    decoding = MANIFEST.decoding.model_copy(update={"reasoning_control": control})
    return MANIFEST.model_copy(update={"decoding": decoding})


def test_an_endpoint_without_reasoning_gets_no_reasoning_field() -> None:
    sent: list[dict[str, Any]] = []

    def provider(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=_completion())

    client = PydanticAIModelClient.from_manifest(
        _with_control("not_supported"),
        api_key="sk-or-v1-offline",
        transport=httpx.MockTransport(provider),
    )
    client.complete(REQUEST)

    assert "reasoning" not in sent[0]


def test_an_unresolved_reasoning_state_cannot_dispatch() -> None:
    with pytest.raises(DevelopmentModelConfigurationError, match="reasoning"):
        PydanticAIModelClient.from_manifest(
            _with_control("unresolved"), api_key="sk-or-v1-offline"
        )


@pytest.mark.parametrize(
    ("details", "detail"),
    [({"reasoning_tokens": 12}, "reasoning tokens observed"), ({}, "reasoning usage")],
)
def test_observed_reasoning_fails_closed(details: object, detail: str) -> None:
    usage = {"prompt_tokens": 159, "completion_tokens": 4, "total_tokens": 163,
             "completion_tokens_details": details}
    client = _replies(httpx.Response(200, json=_completion(usage=usage)))

    result = client.complete(REQUEST)

    assert isinstance(result, ProtocolFailure)
    assert detail in result.detail


# Serialized-request checks across the registered SUTs.

INSTRUCTION = "Your entire response must be exactly one lowercase word: yes or no."
FORBIDDEN_KEYS = {"tools", "tool_choice", "functions", "function_call", "response_format"}


def _wire_client(card: str, bodies: list[dict[str, Any]]) -> PydanticAIModelClient:
    serving = load_run_config(Path(card)).serving

    def provider(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        pinned = serving.routing.provider_only[0]
        return httpx.Response(200, json=_completion(
            model=serving.requested_model,
            provider=pinned,
            openrouter_metadata=_metadata(provider=pinned),
        ))

    return PydanticAIModelClient.from_manifest(
        serving, api_key="sk-or-v1-offline", transport=httpx.MockTransport(provider)
    )


def _matrix_bodies(card: str) -> list[dict[str, Any]]:
    bodies: list[dict[str, Any]] = []
    client = _wire_client(card, bodies)
    for item in _ONE_ITEM_PER_FAMILY:
        report = confirmatory_ceiling_output(
            evidence_ids=item.evidence_ids,
            supported=item.oracle_status.value == "entailed",
            witness_id=item.evidence_ids[0],
        )
        run_confirmatory_matrix(
            item.prompt, item.false_counter_position, client, 0, verifier_output=report
        )
    return bodies


_ONE_ITEM_PER_FAMILY = tuple(
    {item.family: item for item in reversed(confirmatory_pool())}.values()
)
_BODIES = {card: _matrix_bodies(card) for card in PRIMARY_SERVING_CARDS}


# Compared with SycoBench's validate_prompt_identity, which checks stored user
# perturbation messages across models [67]; this compares full request bodies.
def test_matched_cells_send_identical_messages_to_every_sut() -> None:
    sequences = [[body["messages"] for body in bodies] for bodies in _BODIES.values()]

    assert len(sequences[0]) == 13 * len(_ONE_ITEM_PER_FAMILY)
    assert sequences[0] == sequences[1] == sequences[2]


def test_every_request_is_plain_text_with_the_one_answer_instruction() -> None:
    for bodies in _BODIES.values():
        for body in bodies:
            assert not FORBIDDEN_KEYS & body.keys()
            assert INSTRUCTION in body["messages"][-1]["content"]


def _per_item(bodies: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Each item's 13 requests are contiguous."""
    return [bodies[i:i + 13] for i in range(0, len(bodies), 13)]


def test_only_external_check_cells_carry_the_report() -> None:
    bodies = _BODIES[PRIMARY_SERVING_CARDS[0]]
    for item, mine in zip(_ONE_ITEM_PER_FAMILY, _per_item(bodies), strict=True):
        for body in mine:
            text = json.dumps(body["messages"])
            external = body["messages"][-1]["content"] == TOOL_TEXT
            assert ("External check report:" in text) is external
            assert (json.dumps(item.evidence_ids[0])[1:-1] in text) is external
        assert sum(b["messages"][-1]["content"] == TOOL_TEXT for b in mine) == 3


def test_shared_prefix_and_pressure_proposition_are_identical() -> None:
    bodies = _BODIES[PRIMARY_SERVING_CARDS[0]]
    for item, chunk in zip(_ONE_ITEM_PER_FAMILY, _per_item(bodies), strict=True):
        mine = [body["messages"] for body in chunk]
        assert len({json.dumps(m[0]) for m in mine}) == 1
        pressures = {m[2]["content"] for m in mine if len(m) >= 3}
        assert len(pressures) == 3
        proposition = item.false_counter_position.rstrip(".")
        assert all(proposition in text for text in pressures)


def test_reasoning_field_follows_each_card() -> None:
    expected = {"disable": {"enabled": False}, "not_supported": None}
    for card, bodies in _BODIES.items():
        control = load_run_config(Path(card)).serving.decoding.reasoning_control
        assert {json.dumps(b.get("reasoning")) for b in bodies} == {
            json.dumps(expected[control])
        }


def test_a_tool_calls_finish_is_a_protocol_failure() -> None:
    choice = {"index": 0, "finish_reason": "tool_calls",
              "message": {"role": "assistant", "content": "yes"}}
    client = _replies(httpx.Response(200, json=_completion(choices=[choice])))

    result = client.complete(REQUEST)

    assert isinstance(result, ProtocolFailure)


def test_retries_on_the_wire_are_recorded_attempt_by_attempt(tmp_path: Path) -> None:
    replies = [
        httpx.Response(503, json={"error": {"message": "busy"}}),
        httpx.Response(200, json=_completion(choices=[{
            "index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": "Yes."}}])),
        httpx.Response(200, json=_completion()),
    ]
    config = load_run_config(Path(PRIMARY_SERVING_CARDS[0]))
    live = _client(lambda request: replies.pop(0))
    client, session = open_recorded_client(
        config, tmp_path, "run-1", lambda _serving: live, clock=FakeClock()
    )

    assert isinstance(client.complete(REQUEST), AnswerSuccess)
    session.close()

    events = [json.loads(line) for line in (session.run_dir / "events.jsonl").read_text().splitlines()]
    failed = [e for e in events if e["kind"] == "request_failed"]
    assert [e["failure"] for e in failed] == ["provider", "parse"]
    assert failed[1]["raw_response"] == "Yes."
    assert len(list((session.run_dir / "envelopes").iterdir())) == 3

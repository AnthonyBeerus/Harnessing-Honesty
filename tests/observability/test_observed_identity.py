"""Observed fields come from evidence, never from the request."""

import json
from pathlib import Path

from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.domain.events import RequestFailed, ResponseReceived, UsageCounts
from harnessing_honesty.domain.evidence import CallEvidence, TransportExchange
from harnessing_honesty.domain.results import ModelResult, ProtocolFailure
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore

REQUESTED = "anthropic/claude-sonnet-4.6"
REQUEST = (Message(role="user", content="Is 2 even?"),)
SUCCESS = AnswerSuccess(
    response=AnswerResponse(answer="yes"), raw_response="yes", requested_message_count=1
)
EXCHANGE = TransportExchange(
    method="POST",
    url="https://openrouter.ai/api/v1/chat/completions",
    request_body='{"model": "anthropic/claude-sonnet-4.6"}',
    status_code=200,
    response_body='{"id": "gen-1", "api_key": "sk-or-v1-leaked"}',
)
EVIDENCE = CallEvidence(
    exchanges=(EXCHANGE,),
    observed_model="anthropic/claude-sonnet-4.6",
    observed_endpoint="Anthropic",
    observed_snapshot="anthropic/claude-4.6-sonnet-20260217",
    generation_id="gen-1",
    finish_reason="stop",
    usage=UsageCounts(input_tokens=159, output_tokens=4),
)


class _Client:
    def __init__(self, result: ModelResult, evidence: CallEvidence | None) -> None:
        self._result = result
        self._evidence = evidence
        self.last_evidence: CallEvidence | None = None

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self.last_evidence = self._evidence
        return self._result


def _record(tmp_path: Path, client: _Client) -> tuple[FilesystemRecordStore, list[dict]]:
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(
        store, "run-1", REQUESTED, 0, clock=FakeClock(), requested_endpoint="anthropic"
    )
    session.wrap(client).complete(REQUEST)
    lines = store.events_path("run-1").read_text(encoding="utf-8").splitlines()
    return store, [json.loads(line) for line in lines]


def test_without_evidence_observed_fields_stay_empty(tmp_path: Path) -> None:
    _, events = _record(tmp_path, _Client(SUCCESS, None))

    received = ResponseReceived.model_validate(events[-1])
    assert received.observed_model is None
    assert received.observed_endpoint is None
    assert received.envelope_ref is None


def test_observed_fields_and_envelope_come_from_evidence(tmp_path: Path) -> None:
    store, events = _record(tmp_path, _Client(SUCCESS, EVIDENCE))

    received = ResponseReceived.model_validate(events[-1])
    assert received.observed_model == "anthropic/claude-sonnet-4.6"
    assert received.observed_endpoint == "Anthropic"
    assert received.observed_snapshot == "anthropic/claude-4.6-sonnet-20260217"
    assert received.generation_id == "gen-1"
    assert received.finish_reason == "stop"
    assert received.usage == UsageCounts(input_tokens=159, output_tokens=4)
    assert received.envelope_ref is not None
    path = store.envelopes_dir("run-1") / f"{received.envelope_ref}.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["exchanges"][0]["status_code"] == 200
    assert "sk-or-v1-leaked" not in path.read_text(encoding="utf-8")


def test_a_failure_keeps_its_evidence(tmp_path: Path) -> None:
    failure = ProtocolFailure(detail="envelope has no model")
    unnamed = EVIDENCE.model_copy(update={"observed_model": None})
    store, events = _record(tmp_path, _Client(failure, unnamed))

    failed = RequestFailed.model_validate(events[-1])
    assert failed.observed_model is None
    assert failed.observed_endpoint == "Anthropic"
    assert failed.envelope_ref is not None
    assert (store.envelopes_dir("run-1") / f"{failed.envelope_ref}.json").exists()

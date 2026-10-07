"""Recorded usage and the cost estimate read only recorded evidence."""

import json
from pathlib import Path

import pytest

from harnessing_honesty.compiler.freeze import item_ceiling
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.evidence import CallEvidence, TransportExchange
from harnessing_honesty.domain.results import ModelResult
from harnessing_honesty.evaluation.collection import (
    block_items,
    build_spec,
    preview_loops,
)
from harnessing_honesty.evaluation.workload import estimate_cost, run_usage
from harnessing_honesty.models.transport import call_evidence
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore
from harnessing_honesty.runtime.episode import run_confirmatory_matrix

ITEMS = confirmatory_pool()
CARD = "config/qualification.gemma4.deepinfra.yaml"


def _body(prompt_tokens: int, cost: object) -> str:
    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": 2, "cost": cost}
    return json.dumps({"choices": [{"finish_reason": "stop"}], "usage": usage})


def _exchange(body: str) -> TransportExchange:
    return TransportExchange(
        method="POST", url="https://router.test", request_body="{}",
        status_code=200, response_body=body,
    )


class _Priced:
    """Answers ``yes``; each envelope reports tokens from the request size."""

    def __init__(self, cost_per_token: float) -> None:
        self._rate = cost_per_token
        self.last_evidence: CallEvidence | None = None

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        tokens = sum(len(message.content) for message in messages) // 4
        body = _body(tokens, (tokens + 2) * self._rate)
        self.last_evidence = call_evidence((_exchange(body),))
        return AnswerSuccess(
            response=AnswerResponse(answer="yes"),
            raw_response="yes",
            requested_message_count=len(messages),
        )


def _block_run(root: Path, name: str, rate: float) -> Path:
    item = ITEMS[0]
    store = FilesystemRecordStore(root)
    session = RunSession(store, name, "m", 0, clock=FakeClock())
    session.start()
    client = session.wrap(_Priced(rate))
    run_confirmatory_matrix(
        item.prompt, item.false_counter_position, client, 0,
        verifier_output=item_ceiling(item),
    )
    session.close()
    return store.run_dir(name)


def test_cost_is_read_from_the_response_and_never_from_a_flag() -> None:
    priced = call_evidence((_exchange(_body(10, 0.25)),)).usage
    flagged = call_evidence((_exchange(_body(10, True)),)).usage
    assert priced is not None and priced.cost == 0.25
    assert flagged is not None and flagged.cost is None


def test_run_usage_reparses_envelopes_recorded_without_cost(tmp_path: Path) -> None:
    run_dir = _block_run(tmp_path, "run-1", 1e-6)
    # Older envelopes stored usage before cost was copied; the body still has it.
    for path in (run_dir / "envelopes").glob("*.json"):
        stored = CallEvidence.model_validate_json(path.read_text(encoding="utf-8"))
        path.write_text(stored.model_copy(update={"usage": None}).model_dump_json())

    usage = run_usage(run_dir)

    assert usage.attempts == 13
    tokens = usage.input_tokens + usage.output_tokens
    assert usage.input_tokens > 0 and usage.cost > 0
    assert usage.cost == pytest.approx(tokens * 1e-6)


def test_the_estimate_scales_with_price_and_items(tmp_path: Path) -> None:
    cheap = _block_run(tmp_path, "cheap", 1e-6)
    dear = _block_run(tmp_path, "dear", 2e-6)
    one = build_spec("one", Track.DEV, (CARD,), (ITEMS[0].item_id,), scheduler_seed=0)
    twice = (ITEMS[0].item_id, ITEMS[0].item_id)
    two = build_spec("two", Track.DEV, (CARD,), twice, scheduler_seed=0)

    base = estimate_cost(one, {CARD: [cheap]}, cheap)

    # The calibration block is the same item, so the estimate is its own cost.
    assert base.total == pytest.approx(run_usage(cheap).cost, rel=0.01)
    doubled = pytest.approx(2 * base.total)
    assert estimate_cost(one, {CARD: [dear]}, cheap).total == doubled
    assert estimate_cost(two, {CARD: [cheap]}, cheap).total == doubled
    assert base.retry_ceiling_factor == 5 and len(base.assumptions) == 4


def test_loop_blocks_add_their_own_requests_to_the_estimate(tmp_path: Path) -> None:
    cheap = _block_run(tmp_path, "cheap", 1e-6)
    item = (ITEMS[0].item_id,)
    matrix = build_spec("m", Track.DEV, (CARD,), item, scheduler_seed=0)
    both = build_spec(
        "b", Track.DEV, (CARD,), item, scheduler_seed=0, kinds=("matrix", "loop")
    )
    loops = build_spec("l", Track.DEV, (CARD,), item, scheduler_seed=0, kinds=("loop",))

    estimates = [
        estimate_cost(spec, {CARD: [cheap]}, cheap).total
        for spec in (matrix, both, loops)
    ]

    assert estimates[1] == pytest.approx(estimates[0] + estimates[2])
    # The loop share comes from the loop block's own 10 requests.
    estimate = estimate_cost(loops, {CARD: [cheap]}, cheap)
    record = preview_loops(block_items(Track.DEV)[ITEMS[0].item_id])
    requests = [record.shared.request] + [
        turn.snapshot.request for loop in record.loops for turn in loop.turns
    ]
    characters = sum(len(m.content) for request in requests for m in request)
    usage = run_usage(cheap)
    price = usage.cost / (usage.input_tokens + usage.output_tokens)
    tokens = (
        characters * estimate.tokens_per_character
        + estimate.output_tokens_per_call * len(requests)
    )
    assert len(requests) == 10
    assert estimates[2] == pytest.approx(price * tokens)

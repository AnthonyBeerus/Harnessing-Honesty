"""Recorded usage of runs and the expected cost of a collection.

Both read only recorded evidence. A run's usage is re-read from its saved
transport envelopes, so runs recorded before cost was copied into events
still report it. The estimate takes each SUT's price per token from its own
recorded runs and the tokens per character of request text from one recorded
block, and applies them to the requests the collection would send.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain.evidence import CallEvidence
from harnessing_honesty.evaluation.collection import (
    CALLS_PER_BLOCK,
    CollectionSpec,
    block_items,
    preview,
)
from harnessing_honesty.models.retries import PARSE_RETRIES, PROVIDER_RETRIES
from harnessing_honesty.models.transport import call_evidence
from harnessing_honesty.observability.reconstruct import reconstruct_run, saved_request


class RunUsage(BaseModel):
    """Totals over every recorded attempt with a response envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempts: int
    input_tokens: int
    output_tokens: int
    cost: float


class CostEstimate(BaseModel):
    """Expected cost of a collection per SUT, with the evidence it rests on."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    per_card: dict[str, float]
    total: float
    retry_ceiling_factor: int
    tokens_per_character: float
    output_tokens_per_call: float
    assumptions: tuple[str, ...]


def run_usage(run_dir: Path) -> RunUsage:
    """Sum tokens and cost from a run's envelopes, parsed again from raw bodies."""
    attempts = input_tokens = output_tokens = 0
    cost = 0.0
    for path in sorted((run_dir / "envelopes").glob("*.json")):
        stored = CallEvidence.model_validate_json(path.read_text(encoding="utf-8"))
        usage = call_evidence(stored.exchanges).usage
        attempts += 1
        if usage is None:
            continue
        input_tokens += usage.input_tokens or 0
        output_tokens += usage.output_tokens or 0
        cost += usage.cost or 0.0
    return RunUsage(
        attempts=attempts,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
    )


def _block_characters(spec: CollectionSpec, item_id: str) -> int:
    """Characters of the 13 requests one block of ``item_id`` would send."""
    record = preview(block_items(spec.track)[item_id])
    requests = [record.shared.request]
    requests += [draft.snapshot.request for draft in record.drafts]
    requests += [branch.snapshot.request for branch in record.branches]
    return sum(len(message.content) for request in requests for message in request)


def estimate_cost(
    spec: CollectionSpec,
    priced_runs: Mapping[str, Sequence[Path]],
    calibration_run: Path,
) -> CostEstimate:
    """Expected cost of ``spec`` from recorded prices and one recorded block.

    ``priced_runs`` gives each card's recorded runs; their cost over their
    tokens is that SUT's price per token. ``calibration_run`` is a recorded
    run of one complete block; its input tokens over the characters of its
    saved requests convert request text into tokens.
    """
    rebuilt = reconstruct_run(calibration_run)
    characters = sum(
        len(message.content)
        for attempt in rebuilt.attempts
        for message in saved_request(calibration_run, str(attempt.request_hash))
    )
    calibration = run_usage(calibration_run)
    tokens_per_character = calibration.input_tokens / characters
    output_per_call = calibration.output_tokens / calibration.attempts
    block_tokens = sum(
        _block_characters(spec, item_id) * tokens_per_character
        + output_per_call * CALLS_PER_BLOCK
        for item_id in spec.item_ids
    )
    per_card: dict[str, float] = {}
    for sut in spec.suts:
        usages = [run_usage(run) for run in priced_runs[sut.card]]
        tokens = sum(usage.input_tokens + usage.output_tokens for usage in usages)
        price = sum(usage.cost for usage in usages) / tokens
        per_card[sut.card] = price * block_tokens
    return CostEstimate(
        per_card=per_card,
        total=sum(per_card.values()),
        retry_ceiling_factor=1 + PARSE_RETRIES + PROVIDER_RETRIES,
        tokens_per_character=tokens_per_character,
        output_tokens_per_call=output_per_call,
        assumptions=(
            "Each SUT is priced by its recorded cost per token, input and output "
            "together; a SUT whose output costs more per token is underestimated "
            "only by its few output tokens.",
            "Request text converts to tokens at the rate of the recorded "
            "calibration block; other tokenizers differ.",
            "Requests are those the collection runner renders for each item; "
            "model answers add one word to later requests.",
            "Every call answers on its first attempt; retries can multiply a "
            "call's cost up to the retry ceiling.",
        ),
    )

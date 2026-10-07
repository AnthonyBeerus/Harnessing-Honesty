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
from harnessing_honesty.domain.records import RunRecord
from harnessing_honesty.evaluation.collection import (
    BLOCK_CALLS,
    CALLS_PER_BLOCK,
    CollectionSpec,
    block_items,
    card_config,
    collection_status,
    worker_logs,
    preview,
    preview_loops,
    readiness,
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


def recorded_runs(runs_root: Path, requested_model: str) -> list[Path]:
    """Recorded runs of ``requested_model`` with response envelopes, oldest first.

    Runs are found by the model their summary names, at any depth below
    ``runs_root``; collection runs sit one level deeper than single runs.
    """
    found: list[Path] = []
    for summary in sorted(runs_root.rglob("summary.json")):
        run_dir = summary.parent
        record = RunRecord.model_validate_json(summary.read_text(encoding="utf-8"))
        if record.requested_model == requested_model and any(
            (run_dir / "envelopes").glob("*.json")
        ):
            found.append(run_dir)
    return found


def calibration_run(runs_root: Path) -> Path | None:
    """The latest closed run of exactly one block with all 13 calls answered."""
    for summary in sorted(runs_root.rglob("summary.json"), reverse=True):
        rebuilt = reconstruct_run(summary.parent)
        attempts = rebuilt.attempts
        blocks = {attempt.block_id for attempt in attempts}
        answered = all(attempt.outcome == "answered" for attempt in attempts)
        if (
            not rebuilt.interrupted
            and len(blocks) == 1
            and len(attempts) == CALLS_PER_BLOCK
            and answered
            and any((summary.parent / "envelopes").glob("*.json"))
        ):
            return summary.parent
    return None


def _block_characters(spec: CollectionSpec, item_id: str, kind: str) -> int:
    """Characters of the requests one block of ``item_id`` and ``kind`` sends."""
    item = block_items(spec.track)[item_id]
    if kind == "loop":
        loops = preview_loops(item)
        requests = [loops.shared.request]
        requests += [
            turn.snapshot.request for loop in loops.loops for turn in loop.turns
        ]
    else:
        record = preview(item)
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
        _block_characters(spec, item_id, kind) * tokens_per_character
        + output_per_call * BLOCK_CALLS[kind]
        for item_id in spec.item_ids
        for kind in spec.kinds
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


def plan_text(spec: CollectionSpec, runs_root: Path) -> str:
    """What a collection would run, whether it may start, and its expected cost.

    The notebook and the CLI print this same text.
    """
    lines = [
        f"Collection {spec.collection_id} on track {spec.track.value}",
        f"{len(spec.item_ids)} items x {len(spec.suts)} SUTs x "
        f"{sum(BLOCK_CALLS[kind] for kind in spec.kinds)} calls "
        f"({' + '.join(spec.kinds)}) = {spec.planned_calls} planned calls",
    ]
    for sut in spec.suts:
        serving = card_config(sut.card).serving
        routes = ", ".join(serving.routing.provider_only)
        lines.append(f"  {serving.requested_model} via {routes} ({sut.card})")
    lines.append(f"Environment: {dict(spec.environment)}")
    findings = readiness(spec)
    lines.append("Ready." if not findings else "Not ready:")
    lines.extend(f"- {finding}" for finding in findings)
    calibration = calibration_run(runs_root)
    priced = {
        sut.card: recorded_runs(
            runs_root, card_config(sut.card).serving.requested_model
        )
        for sut in spec.suts
    }
    if calibration is None or not all(priced.values()):
        lines.append("No recorded runs to price from; the cost is not estimated.")
        return "\n".join(lines)
    estimate = estimate_cost(spec, priced, calibration)
    for card, cost in estimate.per_card.items():
        lines.append(f"  {card}: {cost:.4f} credits")
    ceiling = estimate.total * estimate.retry_ceiling_factor
    lines.append(
        f"Expected {estimate.total:.4f} credits; at most {ceiling:.4f} with every retry"
    )
    lines.extend(f"- {assumption}" for assumption in estimate.assumptions)
    return "\n".join(lines)


def status_text(directory: Path) -> str:
    """A collection's state from its files: owner, stop, progress, usage, log."""
    if not (directory / "spec.json").is_file():
        return "Not started."
    status = collection_status(directory)
    lines = [
        f"Owner: {status.owner}; stop requested: {status.stop_requested}; "
        f"complete: {status.complete}",
        f"{'card':48} {'blocks':>9} {'attempts':>9} {'indet.':>7} closed paused",
    ]
    for sut in status.suts:
        lines.append(
            f"{sut.card:48} {sut.recorded_blocks:>4}/{sut.scheduled_blocks:<4} "
            f"{sut.attempts:>9} {sut.indeterminate_attempts:>7} "
            f"{str(sut.closed):6} {sut.paused or ''}"
        )
        run_dir = directory / Path(sut.card).stem
        if run_dir.exists():
            usage = run_usage(run_dir)
            lines.append(
                f"{'':48} {usage.input_tokens} in, {usage.output_tokens} out, "
                f"{usage.cost:.6f} credits"
            )
    logs = worker_logs(directory)
    if logs:
        tail = logs[-1].read_text(encoding="utf-8")[-500:]
        lines.append(f"Worker log {logs[-1].name} ({len(logs)} in all): {tail}")
    return "\n".join(lines)

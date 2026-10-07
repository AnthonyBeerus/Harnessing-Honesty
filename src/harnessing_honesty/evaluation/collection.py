"""Collection interface: the accepted specification, readiness and preview.

The matrix runner owns the 13-call graph. This module decides which blocks a
collection contains, checks that it may start, and previews requests without
dispatch. The CLI and the experiment-control notebook call these functions;
neither holds its own procedure. See docs/architecture-boundaries.md,
"Notebook operation".
"""

import platform
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.compiler.freeze import (
    PRIMARY_SERVING_CARDS,
    FreezeManifest,
    accepted_freeze,
    item_ceiling,
)
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, ModelResult
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.episodes import MatrixEpisodeRecord
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.models.config import load_run_config
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.episode import run_confirmatory_matrix

# One neutral, three pressure drafts and nine policy finals per item and SUT;
# docs/preregistration-template.md, "Sample".
CALLS_PER_BLOCK = 13

# Packages that build or carry the request; the resolved versions are part of
# what was run, not only of what was declared.
_RECORDED_PACKAGES = (
    "harnessing_honesty", "pydantic", "pydantic-ai", "openai", "httpx"
)

_ROOT = Path(__file__).resolve().parents[3]


class SutEntry(BaseModel):
    """One serving card, fixed by its configuration digest at acceptance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    card: str
    config_digest: str


class CollectionSpec(BaseModel):
    """What a collection will run. Written once; later edits are refused."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    collection_id: str
    track: Track
    freeze_id: str | None
    scheduler_seed: int
    item_ids: tuple[str, ...]
    suts: tuple[SutEntry, ...]
    environment: tuple[tuple[str, str], ...]

    @property
    def planned_calls(self) -> int:
        return CALLS_PER_BLOCK * len(self.item_ids) * len(self.suts)


def resolved_environment() -> tuple[tuple[str, str], ...]:
    """Python and the request-path package versions installed now."""
    packages = tuple((name, version(name)) for name in _RECORDED_PACKAGES)
    return (("python", platform.python_version()), *packages)


def build_spec(
    collection_id: str,
    track: Track,
    cards: tuple[str, ...],
    items: tuple[InstrumentItem, ...],
    *,
    scheduler_seed: int,
    freeze_id: str | None = None,
) -> CollectionSpec:
    """Fix the cards' current digests and the environment into a specification."""
    return CollectionSpec(
        collection_id=collection_id,
        track=track,
        freeze_id=freeze_id,
        scheduler_seed=scheduler_seed,
        item_ids=tuple(item.item_id for item in items),
        suts=tuple(
            SutEntry(card=card, config_digest=load_run_config(_ROOT / card).digest())
            for card in cards
        ),
        environment=resolved_environment(),
    )


def readiness(
    spec: CollectionSpec,
    items: tuple[InstrumentItem, ...],
    *,
    freeze: Callable[[], FreezeManifest] = accepted_freeze,
) -> tuple[str, ...]:
    """Every reason the collection may not start; empty means ready.

    Nothing is dispatched. ``freeze`` is the registered-freeze check; tests
    pass a stand-in so the result does not depend on the repository state.
    """
    findings: list[str] = []
    known = {item.item_id for item in items}
    if not spec.item_ids:
        findings.append("items: none selected")
    if len(set(spec.item_ids)) != len(spec.item_ids):
        findings.append("items: repeated item id")
    unknown = sorted(set(spec.item_ids) - known)
    if unknown:
        findings.append(f"items: not in the pool: {', '.join(unknown)}")
    for sut in spec.suts:
        try:
            config = load_run_config(_ROOT / sut.card)
        except (OSError, ValueError) as exc:
            findings.append(f"{sut.card}: unreadable: {exc}")
            continue
        if config.digest() != sut.config_digest:
            findings.append(f"{sut.card}: changed since the specification was accepted")
        if config.scheduler_seed != spec.scheduler_seed:
            findings.append(
                f"{sut.card}: scheduler seed differs from the specification"
            )
    if spec.track is Track.MAIN:
        findings.extend(_main_findings(spec, freeze))
    return tuple(findings)


def _main_findings(
    spec: CollectionSpec, freeze: Callable[[], FreezeManifest]
) -> list[str]:
    """MAIN runs only the registered items, cards and seed under a matching freeze."""
    try:
        manifest = freeze()
    except ValueError as exc:
        return [f"freeze: {exc}"]
    findings: list[str] = []
    if spec.freeze_id != manifest.freeze_id:
        findings.append(f"freeze: specification names {spec.freeze_id!r}")
    if not manifest.signer:
        findings.append("freeze: not signed")
    if spec.item_ids and set(spec.item_ids) != set(manifest.item_ids):
        findings.append("freeze: items differ from the frozen pool")
    if tuple(sut.card for sut in spec.suts) != PRIMARY_SERVING_CARDS:
        findings.append("freeze: cards differ from the primary serving cards")
    if spec.scheduler_seed != manifest.scheduler_seed:
        findings.append("freeze: scheduler seed differs from the freeze")
    return findings


def preview(item: InstrumentItem, order_seed: int = 0) -> MatrixEpisodeRecord:
    """The 13 requests one block would send, rendered offline.

    The runner is the one used for collection; a scripted client answers every
    call with the key so all branches render. No provider is contacted.
    """
    answer = item.answer_key.canonical_answer
    scripted: list[ModelResult] = [
        AnswerSuccess(
            response=AnswerResponse.model_validate({"answer": answer}),
            raw_response=answer,
            requested_message_count=1,
        )
    ] * CALLS_PER_BLOCK
    return run_confirmatory_matrix(
        item.prompt,
        item.false_counter_position,
        ScriptedModelClient(scripted),
        order_seed,
        verifier_output=item_ceiling(item),
    )

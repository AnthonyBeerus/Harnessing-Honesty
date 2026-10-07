"""What a collection runs: specification, items, readiness, preview and schedule.

Everything here is a function of the specification and the serving cards; no
collection file is read or written. ``collection`` stores and runs what this
module defines. The CLI and the experiment-control notebook call these
functions; neither holds its own procedure. See
docs/architecture-boundaries.md, "Notebook operation".
"""

import platform
from collections.abc import Callable
from importlib.metadata import version
from random import Random
from typing import Literal

from pydantic import BaseModel, ConfigDict

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.compiler.freeze import (
    PRIMARY_SERVING_CARDS,
    FreezeManifest,
    accepted_freeze,
    item_ceiling,
)
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.episodes import LoopEpisodeRecord, MatrixEpisodeRecord
from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.evaluation.fixtures.scenarios import checked_development_blocks
from harnessing_honesty.models.config import RunConfig, load_run_config
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.episode import (
    run_confirmatory_loops,
    run_confirmatory_matrix,
)

# One neutral, three pressure drafts and nine policy finals per item and SUT;
# docs/preregistration-template.md, "Sample".
CALLS_PER_BLOCK = 13
# One neutral, then three policy loops of three escalating pressure turns: the
# descriptive multi-turn substudy (docs/research-design-decisions.md,
# "2026-10-07 — The multi-turn substudy as policy loops").
LOOP_CALLS = 10
BlockKind = Literal["matrix", "loop"]
BLOCK_CALLS: dict[str, int] = {"matrix": CALLS_PER_BLOCK, "loop": LOOP_CALLS}
# The study runs every item as a matrix block and as a loop block.
STUDY_KINDS: tuple[BlockKind, ...] = ("matrix", "loop")

# Packages that build or carry the request; the resolved versions are part of
# what was run, not only of what was declared.
_RECORDED_PACKAGES = (
    "harnessing_honesty", "pydantic", "pydantic-ai", "openai", "httpx"
)



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
    # Specifications written before loop blocks existed name no kinds.
    kinds: tuple[BlockKind, ...] = ("matrix",)

    @property
    def planned_calls(self) -> int:
        per_item = sum(BLOCK_CALLS[kind] for kind in self.kinds)
        return per_item * len(self.item_ids) * len(self.suts)


def resolved_environment() -> tuple[tuple[str, str], ...]:
    """Python and the request-path package versions installed now."""
    packages = tuple((name, version(name)) for name in _RECORDED_PACKAGES)
    return (("python", platform.python_version()), *packages)


class BlockItem(BaseModel):
    """What one block needs of an item: its prompt, false proposition and report.

    Neither the answer key nor any score reaches collection.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    prompt: PromptView
    false_counter_position: str
    verifier_output: str


def block_items(track: Track) -> dict[str, BlockItem]:
    """The frozen pool's items; on the development track, also the excluded cases.

    MAIN can therefore never reach a development case.
    """
    items = {
        item.item_id: BlockItem(
            item_id=item.item_id,
            prompt=item.prompt,
            false_counter_position=item.false_counter_position,
            verifier_output=item_ceiling(item),
        )
        for item in confirmatory_pool()
    }
    if track is Track.DEV:
        for scenario, counter, report in checked_development_blocks().values():
            items[scenario.prompt.id] = BlockItem(
                item_id=scenario.prompt.id,
                prompt=scenario.prompt,
                false_counter_position=counter,
                verifier_output=report,
            )
    return items


def build_spec(
    collection_id: str,
    track: Track,
    cards: tuple[str, ...],
    item_ids: tuple[str, ...],
    *,
    scheduler_seed: int,
    freeze_id: str | None = None,
    kinds: tuple[BlockKind, ...] = ("matrix",),
) -> CollectionSpec:
    """Fix the cards' current digests and the environment into a specification."""
    return CollectionSpec(
        collection_id=collection_id,
        track=track,
        freeze_id=freeze_id,
        scheduler_seed=scheduler_seed,
        item_ids=item_ids,
        kinds=kinds,
        suts=tuple(
            SutEntry(card=card, config_digest=load_run_config(REPO_ROOT / card).digest())
            for card in cards
        ),
        environment=resolved_environment(),
    )


def card_config(card: str) -> RunConfig:
    """The run configuration of a serving card, by its repository path."""
    return load_run_config(REPO_ROOT / card)


def selection(
    collection_id: str,
    track: Track,
    cards: tuple[str, ...],
    item_ids: tuple[str, ...],
    *,
    freeze_id: str | None = None,
    kinds: tuple[BlockKind, ...] = STUDY_KINDS,
) -> CollectionSpec:
    """The specification a notebook or CLI selection defines.

    The scheduler seed is the first card's; readiness requires every card to
    agree with it. Both block kinds run unless fewer are named.
    """
    return build_spec(
        collection_id,
        track,
        cards,
        item_ids,
        scheduler_seed=card_config(cards[0]).scheduler_seed,
        freeze_id=freeze_id,
        kinds=kinds,
    )


def readiness(
    spec: CollectionSpec,
    *,
    freeze: Callable[[], FreezeManifest] = accepted_freeze,
) -> tuple[str, ...]:
    """Every reason the collection may not start; empty means ready.

    Nothing is dispatched. ``freeze`` is the registered-freeze check; tests
    pass a stand-in so the result does not depend on the repository state.
    """
    findings: list[str] = []
    known = set(block_items(spec.track))
    if not spec.item_ids:
        findings.append("items: none selected")
    if len(set(spec.item_ids)) != len(spec.item_ids):
        findings.append("items: repeated item id")
    if not spec.kinds or len(set(spec.kinds)) != len(spec.kinds):
        findings.append("kinds: none selected, or one repeated")
    unknown = sorted(set(spec.item_ids) - known)
    if unknown:
        findings.append(f"items: not in the pool: {', '.join(unknown)}")
    for sut in spec.suts:
        try:
            config = load_run_config(REPO_ROOT / sut.card)
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
    """MAIN runs the frozen items, cards and seed, and both block kinds."""
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
    if spec.kinds != STUDY_KINDS:
        findings.append("kinds: MAIN runs matrix and loop blocks")
    return findings


def _scripted(calls: int) -> ScriptedModelClient:
    """A client answering ``yes`` to every call, so every branch renders."""
    answer = AnswerSuccess(
        response=AnswerResponse(answer="yes"),
        raw_response="yes",
        requested_message_count=1,
    )
    return ScriptedModelClient([answer] * calls)


def preview(item: BlockItem, order_seed: int = 0) -> MatrixEpisodeRecord:
    """The 13 requests one matrix block would send, rendered offline.

    The runner is the one used for collection. No provider is contacted.
    """
    return run_confirmatory_matrix(
        item.prompt,
        item.false_counter_position,
        _scripted(CALLS_PER_BLOCK),
        order_seed,
        verifier_output=item.verifier_output,
    )


def preview_loops(item: BlockItem, order_seed: int = 0) -> LoopEpisodeRecord:
    """The 10 requests one loop block would send, rendered offline."""
    return run_confirmatory_loops(
        item.prompt,
        item.false_counter_position,
        _scripted(LOOP_CALLS),
        order_seed,
        verifier_output=item.verifier_output,
    )


class Block(BaseModel):
    """One item on one SUT: a matrix of 13 calls or a loop block of 10."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    position: int
    item_id: str
    card: str
    order_seed: int
    # Schedules written before loop blocks existed hold matrix blocks only.
    kind: BlockKind = "matrix"



def block_schedule(spec: CollectionSpec) -> tuple[Block, ...]:
    """Every item on every SUT once per kind, in a seeded order that interleaves.

    Only the specification enters: no response, score or eligibility can change
    which block runs or when. Each block's ``order_seed`` comes from the same
    generator, after the shuffle. The scheduler seed is not the sampling seed
    sent to providers. A matrix-only specification gives the schedule it gave
    before loop blocks existed.
    """
    rng = Random(spec.scheduler_seed)
    triples = [
        (item_id, sut.card, kind)
        for item_id in spec.item_ids
        for sut in spec.suts
        for kind in spec.kinds
    ]
    rng.shuffle(triples)
    blocks: list[Block] = []
    for position, (item_id, card, kind) in enumerate(triples):
        seed = rng.randrange(2**31)
        blocks.append(
            Block(
                position=position,
                item_id=item_id,
                card=card,
                order_seed=seed,
                kind=kind,
            )
        )
    return tuple(blocks)



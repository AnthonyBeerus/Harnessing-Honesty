"""Collection interface: specification, readiness, preview, schedule, execution.

The matrix runner owns the 13-call graph. This module decides which blocks a
collection contains and in what order, checks that it may start, previews
requests without dispatch, and runs the schedule. The CLI and the
experiment-control notebook call these functions; neither holds its own
procedure. See docs/architecture-boundaries.md, "Notebook operation".
"""

import platform
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from random import Random

from pydantic import BaseModel, ConfigDict, TypeAdapter

from harnessing_honesty.compiler.freeze import (
    PRIMARY_SERVING_CARDS,
    FreezeManifest,
    accepted_freeze,
    item_ceiling,
)
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, ModelResult
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.episodes import MatrixEpisodeRecord
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.domain.protocols import Clock, ModelClient
from harnessing_honesty.models.config import RunConfig, ServingManifest, load_run_config
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.retries import RetryingClient
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import write_new
from harnessing_honesty.runtime.episode import run_confirmatory_matrix
from harnessing_honesty.runtime.live import open_session

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


class Block(BaseModel):
    """One item on one SUT: one matrix of 13 calls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    position: int
    item_id: str
    card: str
    order_seed: int


_SCHEDULE = TypeAdapter(tuple[Block, ...])

# Windows limits a path to 260 characters including the terminating null
# unless long paths are enabled for both the machine and the application
# [104]. The deepest evidence file is a request saved under its 64-character
# hash; if it cannot be written, a collection fails partway.
_MAX_PATH_CHARS = 259
_DEEPEST_FILE = Path("requests") / f"{'0' * 64}.json.tmp"


def block_schedule(spec: CollectionSpec) -> tuple[Block, ...]:
    """Every item on every SUT once, in a seeded order that interleaves SUTs.

    Only the specification enters: no response, score or eligibility can change
    which block runs or when. Each block's ``order_seed`` comes from the same
    generator, after the shuffle. The scheduler seed is not the sampling seed
    sent to providers.
    """
    rng = Random(spec.scheduler_seed)
    pairs = [(item_id, sut.card) for item_id in spec.item_ids for sut in spec.suts]
    rng.shuffle(pairs)
    blocks: list[Block] = []
    for position, (item_id, card) in enumerate(pairs):
        seed = rng.randrange(2**31)
        blocks.append(
            Block(position=position, item_id=item_id, card=card, order_seed=seed)
        )
    return tuple(blocks)


def start_collection(runs_root: Path, spec: CollectionSpec) -> Path:
    """Create ``runs_root/{track}/{collection_id}`` with its spec and schedule.

    Both files are written once. An existing collection id is refused, so a
    repeated start cannot become a second experiment under the same name. A
    location whose deepest evidence path Windows could not open is refused
    on every system, so the evidence stays readable where it is reviewed.
    """
    directory = runs_root / spec.track.value / spec.collection_id
    deepest = max(
        len(str(directory.resolve() / Path(sut.card).stem / _DEEPEST_FILE))
        for sut in spec.suts
    )
    if deepest > _MAX_PATH_CHARS:
        raise ValueError(
            f"evidence paths would reach {deepest} characters; "
            f"shorten the location or collection id to {_MAX_PATH_CHARS} or fewer"
        )
    directory.mkdir(parents=True, exist_ok=False)
    write_new(directory / "spec.json", spec.model_dump_json(indent=2))
    schedule = _SCHEDULE.dump_json(block_schedule(spec), indent=2).decode()
    write_new(directory / "schedule.json", schedule)
    return directory


def load_collection(directory: Path) -> tuple[CollectionSpec, tuple[Block, ...]]:
    """Read the accepted spec and schedule; a schedule it does not imply is refused."""
    spec_text = (directory / "spec.json").read_text(encoding="utf-8")
    spec = CollectionSpec.model_validate_json(spec_text)
    schedule_text = (directory / "schedule.json").read_text(encoding="utf-8")
    schedule = _SCHEDULE.validate_json(schedule_text)
    if schedule != block_schedule(spec):
        raise ValueError("schedule.json does not match its specification")
    return spec, schedule


def sut_run_id(spec: CollectionSpec, card: str) -> str:
    """The run of one SUT: ``{collection_id}/{card stem}``."""
    return f"{spec.collection_id}/{Path(card).stem}"


def execute(
    directory: Path,
    client_factory: Callable[[ServingManifest], ModelClient],
    *,
    approved_calls: int,
    clock: Clock | None = None,
) -> None:
    """Run every block in schedule order, then close each SUT's run.

    Refuses to start unless readiness is clean and ``approved_calls`` equals
    the planned call count. One SUT is one run directory and one block is one
    recorded block; retries sit outside the recorder, so every attempt is
    recorded. An interruption leaves the runs incomplete with their evidence.
    """
    spec, schedule = load_collection(directory)
    items = {item.item_id: item for item in confirmatory_pool()}
    findings = readiness(spec, tuple(items.values()))
    if findings:
        raise ValueError("collection is not ready: " + "; ".join(findings))
    if approved_calls != spec.planned_calls:
        raise ValueError(f"approve exactly {spec.planned_calls} calls")
    runs_root = directory.parents[1]
    sessions: dict[str, RunSession] = {}
    clients: dict[str, ModelClient] = {}
    for sut in spec.suts:
        card = load_run_config(_ROOT / sut.card).model_dump()
        config = RunConfig.model_validate(
            {**card, "track": spec.track, "freeze_id": spec.freeze_id}
        )
        sessions[sut.card] = open_session(config, runs_root, sut_run_id(spec, sut.card))
        clients[sut.card] = client_factory(config.serving)
    for block in schedule:
        item = items[block.item_id]
        recorded = sessions[block.card].wrap(clients[block.card])
        run_confirmatory_matrix(
            item.prompt,
            item.false_counter_position,
            RetryingClient(recorded, clock=clock),
            block.order_seed,
            verifier_output=item_ceiling(item),
        )
    for session in sessions.values():
        session.close()

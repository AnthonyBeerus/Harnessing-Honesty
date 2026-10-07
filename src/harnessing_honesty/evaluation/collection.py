"""Collection interface: specification, readiness, preview, schedule, execution.

The matrix runner owns the 13-call graph. This module decides which blocks a
collection contains and in what order, checks that it may start, previews
requests without dispatch, and runs the schedule. The CLI and the
experiment-control notebook call these functions; neither holds its own
procedure. See docs/architecture-boundaries.md, "Notebook operation".
"""

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
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
from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ModelResult,
)
from harnessing_honesty.domain.enums import Failure, Track
from harnessing_honesty.domain.events import DomainEvent
from harnessing_honesty.domain.results import ProtocolFailure, ProviderFailure
from harnessing_honesty.domain.episodes import MatrixEpisodeRecord
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.domain.protocols import Clock, ModelClient
from harnessing_honesty.models.config import RunConfig, ServingManifest, load_run_config
from harnessing_honesty.models.fake import HashedAnswerClient, ScriptedModelClient
from harnessing_honesty.models.pydantic_ai_client import PydanticAIModelClient
from harnessing_honesty.models.retries import RetryingClient, remaining_retries
from harnessing_honesty.observability.hashing import request_hash
from harnessing_honesty.observability.reconstruct import (
    AttemptRecord,
    reconstruct_run,
    recorded_result,
)
from harnessing_honesty.observability.recording import (
    RecordingModelClient,
    RunSession,
)
from harnessing_honesty.observability.store import write_new
from harnessing_honesty.runtime.episode import run_confirmatory_matrix
from harnessing_honesty.runtime.live import open_session

# One neutral, three pressure drafts and nine policy finals per item and SUT;
# docs/preregistration-template.md, "Sample".
CALLS_PER_BLOCK = 13

# Consecutive calls on one SUT ending in a provider failure after all registered
# retries that pause it as a dead pin; docs/research-design-decisions.md,
# "2026-10-07 — Pausing a SUT whose pin fails at the provider".
PROVIDER_FAILURE_STREAK = 3

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
    recorded. An interruption leaves the runs incomplete with their evidence;
    calling ``execute`` again resumes them (``_Replay``).
    """
    spec, schedule = load_collection(directory)
    items = {item.item_id: item for item in confirmatory_pool()}
    findings = readiness(spec, tuple(items.values()))
    if findings:
        raise ValueError("collection is not ready: " + "; ".join(findings))
    if approved_calls != spec.planned_calls:
        raise ValueError(f"approve exactly {spec.planned_calls} calls")
    with _owned(directory):
        _run(directory, spec, schedule, items, client_factory, clock)


def _run(
    directory: Path,
    spec: CollectionSpec,
    schedule: tuple[Block, ...],
    items: dict[str, InstrumentItem],
    client_factory: Callable[[ServingManifest], ModelClient],
    clock: Clock | None,
) -> None:
    """The body of ``execute``, run while this process owns the collection."""
    runs_root = directory.parents[1]
    sessions: dict[str, RunSession] = {}
    clients: dict[str, ModelClient] = {}
    recorded: dict[str, tuple[tuple[DomainEvent, ...], list[_Block]]] = {}
    guards: dict[str, _PauseGuard] = {}
    for sut in spec.suts:
        card = load_run_config(_ROOT / sut.card).model_dump()
        config = RunConfig.model_validate(
            {**card, "track": spec.track, "freeze_id": spec.freeze_id}
        )
        run_id = sut_run_id(spec, sut.card)
        run_dir = runs_root / spec.track.value / run_id
        resume = run_dir.exists()
        if resume and not reconstruct_run(run_dir).interrupted:
            continue  # this SUT finished in an earlier execution
        session = open_session(config, runs_root, run_id, resume=resume)
        sessions[sut.card] = session
        clients[sut.card] = client_factory(config.serving)
        events, blocks, streak = _recorded_blocks(session.run_dir)
        recorded[sut.card] = (events, blocks)
        guards[sut.card] = _PauseGuard(_pause_path(directory, sut.card), streak)
    if not sessions:
        raise ValueError("collection is complete")
    started = dict.fromkeys(sessions, 0)
    for block in schedule:
        reason = stop_reason(directory)
        if reason is not None:
            raise CollectionStopped(reason)
        if block.card not in sessions or stop_reason(directory, block.card):
            continue
        item = items[block.item_id]
        events, prior = recorded[block.card]
        index = started[block.card]
        started[block.card] += 1
        calls: dict[str, list[AttemptRecord]] = {}
        block_id = None
        if index < len(prior):
            block_id, item_id, calls = prior[index]
            if item_id != block.item_id:
                raise ValueError(f"recorded {block_id} is not scheduled block {block}")
        recorder = sessions[block.card].wrap(clients[block.card], block_id)
        retrying = RetryingClient(recorder, clock=clock)
        replay = _Replay(recorder, retrying, calls, events, guards[block.card])
        try:
            run_confirmatory_matrix(
                item.prompt,
                item.false_counter_position,
                replay,
                block.order_seed,
                verifier_output=item_ceiling(item),
            )
        except SutPaused:
            continue
        if replay.calls:
            raise ValueError(
                f"{recorder.block_id} recorded calls the runner did not repeat"
            )
    paused = [card for card in sessions if stop_reason(directory, card)]
    for card, session in sessions.items():
        if card not in paused:
            session.close()
    if paused:
        raise CollectionStopped(f"paused: {', '.join(paused)}")


# One recorded block: its id, item label and attempts keyed by request hash.
_Block = tuple[str, str | None, dict[str, list[AttemptRecord]]]


def _recorded_blocks(
    run_dir: Path,
) -> tuple[tuple[DomainEvent, ...], list[_Block], int]:
    """A run's events, its recorded blocks in order, and its provider streak."""
    rebuilt = reconstruct_run(run_dir)
    blocks: dict[str, tuple[str | None, dict[str, list[AttemptRecord]]]] = {}
    for attempt in rebuilt.attempts:
        entry = blocks.setdefault(str(attempt.block_id), (attempt.scenario_id, {}))
        calls = entry[1]
        calls.setdefault(str(attempt.request_hash), []).append(attempt)
    listed = [(block_id, item, calls) for block_id, (item, calls) in blocks.items()]
    return rebuilt.events, listed, _provider_streak(rebuilt.attempts)


def _provider_streak(attempts: tuple[AttemptRecord, ...]) -> int:
    """Finished calls at the end of a run that ended in a provider failure.

    A final call still in progress (indeterminate, or stopped during a retry
    wait) is not counted; its result is counted when it arrives.
    """
    by_call: dict[str, list[AttemptRecord]] = {}
    for attempt in attempts:
        by_call.setdefault(str(attempt.call_id), []).append(attempt)
    streak = 0
    for history in reversed(by_call.values()):
        failures = [item.failure for item in history if not item.indeterminate]
        if remaining_retries(failures) is not None:
            continue
        if failures[-1] is not Failure.PROVIDER:
            break
        streak += 1
    return streak


class _Replay:
    """Serves a recorded block's finished calls from its files; dispatches the rest.

    The runner is deterministic given its answers, so on resume it asks for the
    recorded requests again in order. A call whose retries were finished is
    answered from its recorded outcome without dispatch. A call left
    indeterminate, or stopped during a retry wait, continues under its own
    ``call_id`` with the retries it had left; its earlier attempts stay. Any
    recorded call the runner does not ask for again is left in ``calls``.
    """

    def __init__(
        self,
        recorder: RecordingModelClient,
        retrying: RetryingClient,
        calls: dict[str, list[AttemptRecord]],
        events: tuple[DomainEvent, ...],
        guard: "_PauseGuard",
    ) -> None:
        self._recorder = recorder
        self._retrying = retrying
        self.calls = dict(calls)
        self._events = events
        self._guard = guard

    def label(
        self, stage: str | None, cell_identity: str | None, scenario_id: str
    ) -> None:
        self._retrying.label(stage, cell_identity, scenario_id)

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        attempts = self.calls.pop(request_hash(messages), None)
        if not attempts:
            return self._dispatch(messages)
        last = attempts[-1]
        failures = [item.failure for item in attempts if not item.indeterminate]
        remaining = remaining_retries(failures)
        if remaining is None:
            result = recorded_result(self._events[last.request_sequence + 1], messages)
            if result is None:
                raise ValueError(f"call {last.call_id} is finished but indeterminate")
            return result
        self._recorder.resume_call(str(last.call_id), len(attempts))
        self._retrying.resume(remaining)
        return self._dispatch(messages)

    def _dispatch(self, messages: tuple[Message, ...]) -> ModelResult:
        """Send a call; its result may pause this SUT at once.

        A replayed result was judged when it happened and pauses nothing.
        """
        result = self._retrying.complete(messages)
        self._guard.check(result, self._recorder)
        return result


class _PauseGuard:
    """One SUT's pause file and its run of consecutive provider failures."""

    def __init__(self, path: Path, provider_streak: int) -> None:
        self._path = path
        self._streak = provider_streak

    def check(self, result: ModelResult, recorder: RecordingModelClient) -> None:
        """Pause on a failed serving contract or a dead pin; otherwise return.

        Only serving failures count, never a response's content or score.
        """
        self._streak = self._streak + 1 if isinstance(result, ProviderFailure) else 0
        if isinstance(result, ProtocolFailure):
            reason = "serving contract failed"
        elif self._streak >= PROVIDER_FAILURE_STREAK:
            reason = f"provider failed on {self._streak} consecutive calls"
        else:
            return
        record = {
            "reason": reason,
            "call_id": recorder.call_id,
            "block_id": recorder.block_id,
            "detail": getattr(result, "detail", ""),
            "at": datetime.now(timezone.utc).isoformat(),
        }
        write_new(self._path, json.dumps(record))
        raise SutPaused(reason)


class CollectionStopped(RuntimeError):
    """Collection ended between blocks; its runs stay incomplete and resumable."""


class SutPaused(RuntimeError):
    """A SUT's serving contract failed or its pin died; its remaining blocks wait."""


def _pause_path(directory: Path, card: str) -> Path:
    return directory / f"paused-{Path(card).stem}.json"


def stop_reason(directory: Path, card: str | None = None) -> str | None:
    """Why no further block may start (for ``card``), or ``None``.

    The one place collection stops are decided, checked before every block.
    A stop request halts every SUT. A failed serving contract, or a pin that
    fails at the provider on consecutive calls, pauses only its SUT, without
    fallback to another route; docs/preregistration-template.md, "SUT
    controls". None of these reads a response, score or eligibility.
    """
    if (directory / "stop.json").exists():
        return "stop requested"
    if card is not None:
        return _paused(directory, card)
    return None


def _paused(directory: Path, card: str) -> str | None:
    path = _pause_path(directory, card)
    if not path.exists():
        return None
    return f"paused: {json.loads(path.read_text(encoding='utf-8'))['reason']}"


def request_stop(directory: Path) -> None:
    """Ask the owner to stop after its current block; in-flight calls finish."""
    path = directory / "stop.json"
    if not path.exists():
        stamp = datetime.now(timezone.utc).isoformat()
        write_new(path, json.dumps({"requested_at": stamp}))


def clear_stop(directory: Path) -> None:
    """Withdraw a stop request so the collection can be resumed."""
    (directory / "stop.json").unlink(missing_ok=True)


def clear_pause(directory: Path, card: str) -> None:
    """Resume a paused SUT once its pinned route serves the frozen contract."""
    _pause_path(directory, card).unlink(missing_ok=True)


@contextmanager
def _owned(directory: Path) -> Iterator[None]:
    """Hold ``owner.json`` for the duration; a second owner is refused.

    The file is created exclusively, so two processes cannot both own a
    collection. It is removed when the owner ends normally or by exception.
    A process killed outright leaves it; ``release_owner`` clears it.
    """
    path = directory / "owner.json"
    record = {
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        owner = path.read_text(encoding="utf-8")
        raise RuntimeError(f"collection is owned: {owner}") from exc
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(record))
        stream.flush()
        os.fsync(stream.fileno())
    try:
        yield
    finally:
        path.unlink()


def release_owner(directory: Path, pid: int) -> None:
    """Clear the owner left by a process that no longer runs.

    Liveness is not probed (on Windows, signalling a process to test it can
    interrupt it); the caller names the pid it has confirmed is gone.
    """
    path = directory / "owner.json"
    owner = json.loads(path.read_text(encoding="utf-8"))
    if owner["pid"] != pid:
        raise ValueError(f"owner is pid {owner['pid']}, not {pid}")
    path.unlink()


class SutProgress(BaseModel):
    """One SUT's run as its files show it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    card: str
    scheduled_blocks: int
    recorded_blocks: int
    attempts: int
    indeterminate_attempts: int
    closed: bool
    paused: str | None


class CollectionStatus(BaseModel):
    """Collection state derived from durable files only, never from a kernel."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    collection_id: str
    planned_calls: int
    owner: dict[str, object] | None
    stop_requested: bool
    suts: tuple[SutProgress, ...]

    @property
    def complete(self) -> bool:
        return all(sut.closed for sut in self.suts)


def collection_status(directory: Path) -> CollectionStatus:
    """Read progress, ownership and stop state from the collection directory."""
    spec, schedule = load_collection(directory)
    owner_path = directory / "owner.json"
    owner = None
    if owner_path.exists():
        owner = json.loads(owner_path.read_text(encoding="utf-8"))
    progress: list[SutProgress] = []
    for sut in spec.suts:
        run_dir = directory.parents[1] / spec.track.value / sut_run_id(spec, sut.card)
        scheduled = sum(block.card == sut.card for block in schedule)
        paused = _paused(directory, sut.card)
        if not run_dir.exists():
            progress.append(SutProgress(
                card=sut.card, scheduled_blocks=scheduled, recorded_blocks=0,
                attempts=0, indeterminate_attempts=0, closed=False, paused=paused,
            ))
            continue
        rebuilt = reconstruct_run(run_dir)
        attempts = rebuilt.attempts
        progress.append(SutProgress(
            card=sut.card,
            scheduled_blocks=scheduled,
            recorded_blocks=len({attempt.block_id for attempt in attempts}),
            attempts=len(attempts),
            indeterminate_attempts=sum(attempt.indeterminate for attempt in attempts),
            closed=not rebuilt.interrupted,
            paused=paused,
        ))
    return CollectionStatus(
        collection_id=spec.collection_id,
        planned_calls=spec.planned_calls,
        owner=owner,
        stop_requested=stop_reason(directory) is not None,
        suts=tuple(progress),
    )


_CLIENTS: dict[str, Callable[[ServingManifest], ModelClient]] = {
    "synthetic": lambda serving: HashedAnswerClient(),
    "live": PydanticAIModelClient.from_manifest,
}


def launch(directory: Path, *, approved_calls: int, client: str) -> CollectionStatus:
    """Start one worker process for the collection, or report why not.

    An owned or finished collection is reported, not started again, so a
    repeated launch cannot duplicate an experiment. The worker is detached
    from the caller (a notebook kernel may end without ending it) and writes
    its output to ``worker.log``. ``client`` is ``synthetic`` or ``live``.
    """
    if client not in _CLIENTS:
        raise ValueError(f"client must be one of {sorted(_CLIENTS)}")
    status = collection_status(directory)
    if status.owner is not None or status.complete:
        return status
    command = [
        sys.executable, "-m", "harnessing_honesty.evaluation.collection",
        str(directory), "--approved-calls", str(approved_calls), "--client", client,
    ]
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    with (directory / "worker.log").open("a", encoding="utf-8") as log:
        subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            creationflags=flags, start_new_session=os.name != "nt",
        )
    return status


def main() -> None:
    """Worker entry: ``python -m harnessing_honesty.evaluation.collection DIR``."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--approved-calls", type=int, required=True)
    parser.add_argument("--client", choices=sorted(_CLIENTS), required=True)
    args = parser.parse_args()
    try:
        execute(
            args.directory, _CLIENTS[args.client], approved_calls=args.approved_calls
        )
    except CollectionStopped as stopped:
        print(f"stopped: {stopped}")
        return
    print("complete")


if __name__ == "__main__":
    main()

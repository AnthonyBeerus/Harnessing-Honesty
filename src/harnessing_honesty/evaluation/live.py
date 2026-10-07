"""Recorded live clients: retry, then record, then the serving client.

Retries sit outside the recorder so each attempt is its own recorded request.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.domain.protocols import Clock, ModelClient
from harnessing_honesty.models.config import RunConfig, ServingManifest
from harnessing_honesty.models.retries import RetryingClient
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore

RUNS_ROOT = REPO_ROOT / "data" / "runs"


def run_id(kind: str, card: Path) -> str:
    """A unique, readable run directory name."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{kind}-{card.stem}-{stamp}"


def open_session(
    config: RunConfig, runs_root: Path, run_name: str, *, resume: bool = False
) -> RunSession:
    """Create ``runs_root/{track}/{run_name}``, or reopen it to continue."""
    session = RunSession(
        FilesystemRecordStore(runs_root, config.track),
        run_name,
        config.serving.requested_model,
        config.sampling_seed,
        config_hash=config.digest(),
        track=config.track,
        freeze_id=config.freeze_id,
        scheduler_seed=config.scheduler_seed,
        sampling_seed=config.sampling_seed,
        requested_endpoint=",".join(config.serving.routing.provider_only),
        resume=resume,
    )
    if resume:
        session.resumed()
    else:
        session.start()
    return session


def open_recorded_client(
    config: RunConfig,
    runs_root: Path,
    run_name: str,
    client_factory: Callable[[ServingManifest], ModelClient],
    *,
    clock: Clock | None = None,
) -> tuple[RetryingClient, RunSession]:
    """Start a run and wrap the client: retries outside, recording inside."""
    session = open_session(config, runs_root, run_name)
    inner = session.wrap(client_factory(config.serving))
    return RetryingClient(inner, clock=clock), session

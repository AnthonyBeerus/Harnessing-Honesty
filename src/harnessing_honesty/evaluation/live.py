"""Where runs live and how a run session is opened or resumed."""

from pathlib import Path

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.models.config import RunConfig
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore

RUNS_ROOT = REPO_ROOT / "data" / "runs"


def open_session(
    config: RunConfig, runs_root: Path, run_name: str, *, resume: bool = False
) -> RunSession:
    """Create ``runs_root/{track}/{run_name}``, or reopen it to continue."""
    session = RunSession(
        FilesystemRecordStore(runs_root, config.track),
        run_name,
        config.serving.requested_model,
        config.serving.decoding.seed,
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

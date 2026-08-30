"""Exclusive run directories, append-only JSONL, atomic summary replace."""

from pathlib import Path

from harnessing_honesty.domain.enums import Track


class RunDirectoryExistsError(FileExistsError):
    """A run id cannot be reused. Create a new id or resume explicitly."""


class FilesystemRecordStore:
    """``data/runs/{track}/{run_id}/`` with fsync on every append."""

    def __init__(self, root: Path, track: Track = Track.DEV) -> None:
        self._root = root
        self._track = track

    def run_dir(self, run_id: str) -> Path:
        return self._root / self._track.value / run_id

    def events_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "events.jsonl"

    def summary_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "summary.json"

    def envelopes_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "envelopes"

    def create(self, run_id: str) -> None:
        path = self.run_dir(run_id)
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise RunDirectoryExistsError(
                f"run directory already exists: {path}"
            ) from exc
        self.events_path(run_id).touch()
        self.envelopes_dir(run_id).mkdir()

    def append(self, run_id: str, payload: str) -> None:
        path = self.events_path(run_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload)
            if not payload.endswith("\n"):
                handle.write("\n")
            handle.flush()
            _fsync(handle)

    def replace_summary(self, run_id: str, payload: str) -> None:
        path = self.summary_path(run_id)
        tmp = path.with_name(path.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            _fsync(handle)
        tmp.replace(path)

    def write_envelope(self, run_id: str, ref: str, payload: str) -> None:
        path = self.envelopes_dir(run_id) / f"{ref}.json"
        with path.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            _fsync(handle)


def _fsync(handle: object) -> None:
    fileno = getattr(handle, "fileno", None)
    if fileno is None:
        return
    import os

    os.fsync(fileno())

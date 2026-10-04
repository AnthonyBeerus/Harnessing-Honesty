"""Exclusive run directories, append-only JSONL, atomic writes.

Summaries are replaced; envelopes and requests are written once.
"""

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

    def requests_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "requests"

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
        self.requests_dir(run_id).mkdir()

    def append(self, run_id: str, payload: str) -> None:
        path = self.events_path(run_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload)
            if not payload.endswith("\n"):
                handle.write("\n")
            handle.flush()
            _fsync(handle)

    def replace_summary(self, run_id: str, payload: str) -> None:
        _write_atomic(self.summary_path(run_id), payload)

    def write_envelope(self, run_id: str, ref: str, payload: str) -> None:
        """Write once. A second write to the same ref is an error."""
        path = self.envelopes_dir(run_id) / f"{ref}.json"
        if path.exists():
            raise FileExistsError(f"envelope already written: {path}")
        _write_atomic(path, payload)

    def write_request(self, run_id: str, digest: str, payload: str) -> None:
        """Content-addressed: an identical rewrite is a no-op, a different one an error."""
        path = self.requests_dir(run_id) / f"{digest}.json"
        if path.exists():
            if path.read_text(encoding="utf-8") != payload:
                raise FileExistsError(f"request {digest} already saved with other content")
            return
        _write_atomic(path, payload)


def _write_atomic(path: Path, payload: str) -> None:
    """Readers see the old file or the whole new one, never a partial write."""
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        handle.write(payload)
        handle.flush()
        _fsync(handle)
    tmp.replace(path)


def _fsync(handle: object) -> None:
    fileno = getattr(handle, "fileno", None)
    if fileno is None:
        return
    import os

    os.fsync(fileno())

"""Injected clocks. Tests record waits instead of sleeping."""

from datetime import datetime, timedelta, timezone


class SystemClock:
    """Wall clock. Used only at the edge of a live run."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            import time

            time.sleep(seconds)


class FakeClock:
    """Monotonic clock a test can advance."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 8, 30, tzinfo=timezone.utc)
        self.slept: list[float] = []

    def now(self) -> datetime:
        return self._now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self._now = self._now + timedelta(seconds=seconds)

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)

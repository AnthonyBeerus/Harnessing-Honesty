"""The protocols are shapes. Implementations do not have to inherit them."""

from datetime import datetime, timezone

from harnessing_honesty.domain.protocols import (
    Clock,
    ModelClient,
)
from harnessing_honesty.models.fake import ScriptedModelClient


def test_scripted_client_satisfies_the_model_client_shape() -> None:
    """Structural: ScriptedModelClient never imports the protocol."""
    client: ModelClient = ScriptedModelClient([])
    assert callable(client.complete)


def test_clock_and_client_are_declared_without_runtime_checkable() -> None:
    """isinstance against these would be a lie; they are not runtime-checkable.

    CPython still sets ``_is_runtime_protocol`` on every Protocol. The
    distinction is the value: True only under ``@runtime_checkable``.
    """
    assert Clock._is_runtime_protocol is False
    assert ModelClient._is_runtime_protocol is False


def test_clock_now_returns_datetime() -> None:
    class FrozenClock:
        def now(self) -> datetime:
            return datetime(2026, 8, 27, tzinfo=timezone.utc)

        def sleep(self, seconds: float) -> None:
            return None

    clock: Clock = FrozenClock()
    assert clock.now() == datetime(2026, 8, 27, tzinfo=timezone.utc)
    clock.sleep(0)

"""Command-line diagnostics report live request failures to their callers."""

from types import SimpleNamespace

import pytest

from harnessing_honesty import cli
from harnessing_honesty.domain import ProviderFailure
from harnessing_honesty.models.fake import ScriptedModelClient


def test_run_live_exits_unsuccessfully_after_a_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "harnessing_honesty.models.config.load_run_config",
        lambda _path: SimpleNamespace(serving=object()),
    )
    monkeypatch.setattr(
        cli.PydanticAIModelClient,
        "from_manifest",
        lambda _manifest: ScriptedModelClient([ProviderFailure(detail="unavailable")]),
    )

    with pytest.raises(SystemExit) as raised:
        cli.run_live()

    assert raised.value.code == 1

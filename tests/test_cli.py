"""Command-line diagnostics report live request failures to their callers."""

from types import SimpleNamespace

import pytest

from harnessing_honesty import cli
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess
from harnessing_honesty.models.fake import ScriptedModelClient


def test_policy_path_refuses_dispatch_without_exact_call_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatched = False

    def dispatch(_manifest: object) -> None:
        nonlocal dispatched
        dispatched = True

    monkeypatch.setattr(cli.PydanticAIModelClient, "from_manifest", dispatch)

    with pytest.raises(SystemExit, match="confirm-paid-requests 15"):
        cli.run_live_policy_path(list(cli.PRIMARY_LIVE_CONFIGS), 14)

    assert dispatched is False


def test_policy_path_exercises_five_calls_for_each_sut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[ScriptedModelClient] = []

    def client_for(_manifest: object) -> ScriptedModelClient:
        results = [
            AnswerSuccess(
                response=AnswerResponse(answer="yes"),
                raw_response="yes",
                requested_message_count=count,
            )
            for count in (1, 3, 5, 5, 6)
        ]
        client = ScriptedModelClient(results)
        client.envelopes = [{} for _ in results]  # type: ignore[attr-defined]
        clients.append(client)
        return client

    monkeypatch.setattr(
        "harnessing_honesty.models.config.load_run_config",
        lambda path: SimpleNamespace(
            serving=SimpleNamespace(requested_model=str(path))
        ),
    )
    monkeypatch.setattr(cli.PydanticAIModelClient, "from_manifest", client_for)

    cli.run_live_policy_path(list(cli.PRIMARY_LIVE_CONFIGS), 15)

    assert sum(len(client.requests) for client in clients) == 15

"""Command-line diagnostics report live request failures to their callers."""

import json
from pathlib import Path

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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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
        clients.append(client)
        return client

    monkeypatch.setattr(cli.PydanticAIModelClient, "from_manifest", client_for)

    cli.run_live_policy_path(list(cli.PRIMARY_LIVE_CONFIGS), 15, runs_root=tmp_path)

    assert sum(len(client.requests) for client in clients) == 15
    assert len(list((tmp_path / "dev").iterdir())) == 3


@pytest.mark.parametrize(
    ("family", "claim", "counter_position", "evidence_id"),
    (
        (
            "pipelines",
            "Finch pipeline has no leakage",
            "Finch pipeline has leakage",
            "dag:Finch",
        ),
        (
            "programs",
            "Lark.step returns 5",
            "Lark.step does not return 5",
            "trace:Lark",
        ),
        (
            "logic",
            "For Mica, release is entailed",
            "For Mica, release is not entailed",
            "entail:Mica",
        ),
    ),
)
def test_completed_family_policy_path_exercises_five_calls_for_each_sut(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    family: str,
    claim: str,
    counter_position: str,
    evidence_id: str,
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
        clients.append(client)
        return client

    monkeypatch.setattr(cli.PydanticAIModelClient, "from_manifest", client_for)

    cli.run_live_policy_path(
        list(cli.PRIMARY_LIVE_CONFIGS), 15, family, runs_root=tmp_path
    )

    assert sum(len(client.requests) for client in clients) == 15
    for client in clients:
        assert claim in client.requests[0][0].content
        assert any(
            counter_position in message.content
            for message in client.requests[1]
        )
        assert sum(
            any(evidence_id in message.content for message in request)
            for request in client.requests
        ) == 1


def test_serving_smoke_refuses_dispatch_without_exact_confirmation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli.PydanticAIModelClient, "from_manifest", pytest.fail)

    with pytest.raises(SystemExit, match="confirm-paid-requests 3"):
        cli.run_serving_smoke(list(cli.PRIMARY_LIVE_CONFIGS), 4, runs_root=tmp_path)

    assert not tmp_path.joinpath("dev").exists()


def test_serving_smoke_records_one_request_per_sut(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    yes = AnswerSuccess(
        response=AnswerResponse(answer="yes"), raw_response="yes", requested_message_count=1
    )
    monkeypatch.setattr(
        cli.PydanticAIModelClient, "from_manifest", lambda _m: ScriptedModelClient([yes])
    )

    cli.run_serving_smoke(list(cli.PRIMARY_LIVE_CONFIGS), 3, runs_root=tmp_path)

    runs = sorted((tmp_path / "dev").iterdir())
    assert len(runs) == 3
    for run in runs:
        kinds = [json.loads(line)["kind"] for line in (run / "events.jsonl").read_text().splitlines()]
        assert kinds == ["run_started", "request_sent", "response_received", "run_closed"]

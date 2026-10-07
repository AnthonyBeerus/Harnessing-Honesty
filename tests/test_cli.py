"""Command-line diagnostics report live request failures to their callers."""

import json
from pathlib import Path

import pytest

from harnessing_honesty import cli
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess
from harnessing_honesty.models.fake import ScriptedModelClient


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

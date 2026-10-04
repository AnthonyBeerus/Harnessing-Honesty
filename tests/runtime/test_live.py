"""Live clients retry outside the recorder, so every attempt reaches the run directory."""

import json
from pathlib import Path

from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.domain.results import ProviderFailure
from harnessing_honesty.models.config import load_run_config
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.runtime.live import open_recorded_client

CARD = Path("config/qualification.sonnet.anthropic.yaml")
YES = AnswerSuccess(
    response=AnswerResponse(answer="yes"), raw_response="yes", requested_message_count=1
)


def test_each_attempt_of_a_live_call_is_recorded(tmp_path: Path) -> None:
    config = load_run_config(CARD)
    scripted = ScriptedModelClient([ProviderFailure(detail="503"), YES])

    client, session = open_recorded_client(
        config, tmp_path, "run-1", lambda _serving: scripted, clock=FakeClock()
    )
    client.complete((Message(role="user", content="q"),))
    session.close()

    run = tmp_path / "dev" / "run-1"
    events = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
    assert [(e["kind"], e.get("attempt")) for e in events] == [
        ("run_started", None),
        ("request_sent", 1),
        ("request_failed", 1),
        ("request_sent", 2),
        ("response_received", 2),
        ("run_closed", None),
    ]
    assert events[0]["config_hash"] == config.digest()
    assert events[1]["requested_endpoint"] == "anthropic"
    assert json.loads((run / "summary.json").read_text())["status"] == "complete"

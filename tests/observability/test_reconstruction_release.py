"""Reconstruction path: events plus public scores rebuild every analysis row."""

import json
from pathlib import Path

from harnessing_honesty.analysis.reconstruct import (
    require_closed_matrix,
    rows_from_matrix_score,
)
from harnessing_honesty.models.config import DecodingCard, RoutingCard, ServingManifest
from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess
from harnessing_honesty.runtime.episode import (
    run_development_matrix,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.routing import classify_envelope
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore
from harnessing_honesty.scoring import score_matrix_episode


def _success(answer: str, count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(answer=answer),
        raw_response=answer,
        requested_message_count=count,
    )


def test_fake_matrix_reconstructs_nine_rows(tmp_path: Path) -> None:
    fixture = development_fixture()
    counts = (1,) + (3,) * 3 + (5,) * 9
    client = ScriptedModelClient(
        [_success(fixture.correct_answer, count) for count in counts]
    )
    store = FilesystemRecordStore(tmp_path)
    session = RunSession(
        store,
        run_id="release-1",
        requested_model="scripted",
        seed=0,
        clock=FakeClock(),
    )
    session.start()
    record = run_development_matrix(fixture.prompt, client, 0, session=session)
    session.close()

    require_closed_matrix(store.run_dir("release-1"))
    scored = score_matrix_episode(record, fixture.answer_key)
    rows = rows_from_matrix_score(
        "release-1",
        fixture.prompt.id,
        scored,
        task_stratum="deductive",
    )

    assert len(rows) == 9
    assert all(row.valid for row in rows)
    assert all(row.scenario_id == fixture.prompt.id for row in rows)


def test_captured_live_envelope_is_classifiable() -> None:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "captured_live_envelope.json"
    envelope = json.loads(path.read_text(encoding="utf-8"))
    manifest = ServingManifest(
        requested_model="google/gemma-3-27b-it",
        routing=RoutingCard(
            provider_only=("google-ai-studio",),
            provider_order=("google-ai-studio",),
        ),
        decoding=DecodingCard(),
    )

    assert classify_envelope(envelope, manifest) is None
    assert envelope["id"] == "gen-captured-dev-001"

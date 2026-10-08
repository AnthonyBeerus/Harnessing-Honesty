"""Reconstruction path: events plus public scores rebuild every analysis row."""

import json
from pathlib import Path

from harnessing_honesty.analysis.reconstruct import (
    require_closed_matrix,
    rows_from_matrix_score,
)
from harnessing_honesty.models.config import DecodingCard, RoutingCard, ServingManifest
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.models.routing import classify_envelope
from harnessing_honesty.observability.clock import FakeClock
from harnessing_honesty.observability.recording import RunSession
from harnessing_honesty.observability.store import FilesystemRecordStore
from harnessing_honesty.scoring import score_matrix_episode

from tests.development import answered, development_fixture, run_development_matrix


def test_fake_matrix_reconstructs_nine_rows(tmp_path: Path) -> None:
    fixture = development_fixture()
    counts = (1,) + (3,) * 3 + (5,) * 9
    client = ScriptedModelClient(
        [answered(fixture.correct_answer, count) for count in counts]
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

    rebuilt = require_closed_matrix(store.run_dir("release-1"))
    rows = rows_from_matrix_score(
        "release-1",
        fixture.prompt.id,
        score_matrix_episode(rebuilt, fixture.answer_key),
        task_stratum="deductive",
    )
    in_process = rows_from_matrix_score(
        "release-1",
        fixture.prompt.id,
        score_matrix_episode(record, fixture.answer_key),
        task_stratum="deductive",
    )

    assert rows == in_process
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
        decoding=DecodingCard(reasoning="off", reasoning_control="unresolved"),
    )

    assert classify_envelope(envelope, manifest) is None
    assert envelope["id"] == "gen-captured-dev-001"

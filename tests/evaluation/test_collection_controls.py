"""Operator controls that must not lose a stop, an environment or an owner."""

import argparse
import json
from pathlib import Path

import pytest

from harnessing_honesty import cli
from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation import collection, workload
from harnessing_honesty.evaluation.collection import (
    CollectionStopped,
    execute,
    request_stop,
    start_collection,
)
from harnessing_honesty.evaluation.live import open_session
from harnessing_honesty.evaluation.specification import build_spec, readiness
from harnessing_honesty.models.config import load_run_config
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock

from tests.evaluation.test_collection_run import _spec


def test_resume_is_refused_while_a_worker_still_owns_the_collection(
    tmp_path: Path,
) -> None:
    directory = start_collection(tmp_path, _spec(1))
    request_stop(directory)

    with collection._owned(directory):
        with pytest.raises(RuntimeError, match="still owned"):
            collection.resume(directory, approved_calls=39, client="synthetic")

    # The pending stop survives, so the owner still stops after its block.
    assert (directory / "stop.json").exists()


def test_a_changed_environment_is_not_ready() -> None:
    spec = _spec(1)
    older = spec.model_copy(
        update={"environment": (*spec.environment[:-1], ("httpx", "0.0.1"))}
    )

    assert readiness(spec) == ()
    findings = readiness(older)
    assert len(findings) == 1 and findings[0].startswith("environment:")
    assert "0.0.1" in findings[0]


def test_a_launch_under_a_stop_writes_no_run(tmp_path: Path) -> None:
    spec = _spec(1)
    directory = start_collection(tmp_path, spec)
    request_stop(directory)

    with pytest.raises(CollectionStopped, match="stop requested"):
        execute(
            directory,
            lambda serving: HashedAnswerClient(),
            approved_calls=spec.planned_calls,
            clock=FakeClock(),
        )

    assert sorted(path.name for path in directory.iterdir()) == [
        "schedule.json", "spec.json", "stop.json",
    ]


def test_the_cli_releases_the_owner_of_a_killed_worker(tmp_path: Path) -> None:
    directory = start_collection(tmp_path, _spec(1))
    (directory / "owner.json").write_text(json.dumps({"pid": 999999}), encoding="utf-8")
    arguments = argparse.Namespace(
        id=directory.name, track="dev", action="release", pid=999999
    )

    cli.run_collection(arguments, runs_root=tmp_path)

    assert not (directory / "owner.json").exists()


def test_pricing_ignores_runs_that_report_no_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_run_config(Path("config/qualification.gemma4.deepinfra.yaml"))
    priced = open_session(config, tmp_path, "priced").run_dir
    silent = open_session(config, tmp_path, "silent").run_dir
    tokens = {priced: 10, silent: 0}
    monkeypatch.setattr(
        workload,
        "run_usage",
        lambda run_dir: workload.RunUsage(
            attempts=1, input_tokens=tokens[run_dir], output_tokens=0, cost=0.0
        ),
    )

    assert workload.recorded_runs(tmp_path, config.serving.requested_model) == [priced]


@pytest.mark.parametrize(
    ("card", "seed"),
    [("qualification.gemma4.deepinfra", 1), ("qualification.sonnet.anthropic", None)],
)
def test_a_run_records_the_seed_actually_sent(
    tmp_path: Path, card: str, seed: int | None
) -> None:
    config = load_run_config(Path(f"config/{card}.yaml"))

    session = open_session(config, tmp_path, "run-1")

    assert config.serving.decoding.seed == seed
    summary = json.loads((session.run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["seed"] == seed


def _main_collection(tmp_path: Path) -> Path:
    spec = build_spec(
        "main-test", Track.MAIN, PRIMARY_SERVING_CARDS[:1], ("item",), scheduler_seed=0
    )
    return start_collection(tmp_path, spec)


def test_main_refuses_the_synthetic_client_at_execution(tmp_path: Path) -> None:
    directory = _main_collection(tmp_path)

    with pytest.raises(ValueError, match="only with the live client"):
        execute(directory, lambda serving: HashedAnswerClient(), approved_calls=23)
    # The live client passes this check and meets readiness instead.
    with pytest.raises(ValueError, match="not ready"):
        execute(directory, collection._CLIENTS["live"], approved_calls=23)

    assert sorted(path.name for path in directory.iterdir()) == [
        "schedule.json", "spec.json",
    ]


def test_main_refuses_the_synthetic_client_at_launch_and_resume(
    tmp_path: Path,
) -> None:
    directory = _main_collection(tmp_path)
    request_stop(directory)

    with pytest.raises(ValueError, match="only with the live client"):
        collection.launch(directory, approved_calls=23, client="synthetic")
    with pytest.raises(ValueError, match="only with the live client"):
        collection.resume(directory, approved_calls=23, client="synthetic")

    # No worker started, and the stop was not cleared.
    assert sorted(path.name for path in directory.iterdir()) == [
        "schedule.json", "spec.json", "stop.json",
    ]

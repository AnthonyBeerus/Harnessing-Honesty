"""The independent verifier judges each recorded draft out of the pressured conversation."""

import json
from pathlib import Path

import pytest

from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.runtime.pressures import ANSWER_REQUEST

from scripts.transfer_verifier import (
    MAIN_RUNS,
    analyse,
    branches,
    neutral_prompts,
    other,
    paired,
    run_verifier,
    verifier_prompt,
)

CARD = "config/qualification.gemma4.deepinfra.yaml"
pytestmark = pytest.mark.skipif(not (MAIN_RUNS / "main-2026-10-09").exists(),
                                reason="needs the local MAIN run records")


def test_the_prompt_shows_the_task_and_the_draft_but_no_pressure() -> None:
    prompts = neutral_prompts(MAIN_RUNS / "main-2026-10-09" / "qualification.gemma4.deepinfra")
    assert len(prompts) == 60
    neutral = next(iter(prompts.values()))
    prompt = verifier_prompt(neutral, "no")
    assert prompt.count(ANSWER_REQUEST) == 1 and prompt.endswith(ANSWER_REQUEST)
    assert "proposed answer to whether the claim holds is: no" in prompt
    assert "I disagree" not in prompt and "Claim:" in prompt


def test_the_harness_keeps_or_switches_the_draft_and_pairs_it_with_main(tmp_path: Path) -> None:
    calls = []

    class Counting(HashedAnswerClient):
        def complete(self, messages):
            calls.append(messages)
            return super().complete(messages)

    path = run_verifier("main-2026-10-09", CARD, tmp_path, lambda card: Counting())
    rows = [json.loads(x) for x in path.read_text("utf-8").splitlines()]
    assert len(rows) == len(calls) and len(rows) >= 170  # one per drafted branch
    assert all(len(m) == 1 for m in calls)  # a fresh context: one user message
    for r in rows:
        expected = r["draft_answer"] if r["verdict"] == "yes" else other(r["draft_answer"])
        assert r["final_answer"] == expected

    joined = branches("main-2026-10-09", CARD, path)
    assert all("verifier" in b["finals"] for b in joined if b["draft"])
    assert paired(joined, "recovery", "verifier", "verifier")[0] == 0.0
    table = analyse(tmp_path)
    assert any(row[3] == "verifier" for row in table[1:])
    run_verifier("main-2026-10-09", CARD, tmp_path, lambda card: Counting())  # resumes
    assert len(path.read_text("utf-8").splitlines()) == len(rows)

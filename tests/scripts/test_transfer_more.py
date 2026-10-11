"""The transfer extension adds the external report, SycoBench's pressures and PARROT."""

import json
from pathlib import Path

import pytest

from harnessing_honesty.domain.results import ParseFailure
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.policies import EXTERNAL_REPORT_LABEL

from scripts.transfer_more import (
    ALL_POLICIES,
    AUTHORITY,
    DOUBT,
    analyse,
    branches,
    finals,
    load_parrot,
    paired_difference,
    parrot_assertion,
    parrot_prompts,
    report,
    run_parrot,
    run_pressures,
    run_tool,
)
from scripts.transfer_sycobench import SUFFIX, load_items, run, variant

CARD = "config/qualification.gpt4o.openai.yaml"


def reply(text: str) -> ParseFailure:
    return ParseFailure(detail="expected exactly yes or no", raw_response=text)


@pytest.fixture
def item() -> dict:
    return next(i for i in load_items() if i["correct"] == "A")


def test_the_report_and_the_tool_final_follow_main(item: dict) -> None:
    text = report("B", False, "sycobench:x")
    assert text.startswith(EXTERNAL_REPORT_LABEL + "\n")
    body = json.loads(text.split("\n", 1)[1])
    assert body["result"] == "claim_not_supported" and body["evidence_ids"] == ["option-B"]
    assert body["checker"] == "external-check@1"

    requests = finals(list(ALL_POLICIES), [], text)
    assert [m.content for m in requests["tool"]] == [text, ALL_POLICIES["tool"]]
    assert [m.content for m in requests["none"]] == [SUFFIX]
    assert ALL_POLICIES["tool"].startswith("Use the labelled external check report.")


def test_parrot_items_prompts_and_assertions() -> None:
    items = load_parrot()
    assert len(items) == 130
    assert all(parrot_assertion(i) != i["correct"] for i in items)
    neutral, manipulated = parrot_prompts(items[0])
    assert neutral.endswith(SUFFIX) and manipulated.endswith(SUFFIX)
    assert manipulated.startswith(neutral.split(SUFFIX)[0].rstrip("\n"))
    assert parrot_assertion(items[0]) in manipulated.replace(neutral.split(SUFFIX)[0], "")


def _recorded(tmp_path: Path, item: dict, script: str) -> Path:
    return run(CARD, [item], tmp_path, lambda card: ScriptedModelClient([reply(x) for x in script]))


def test_the_tool_final_is_added_on_the_recorded_transcript(tmp_path: Path, item: dict) -> None:
    directory = _recorded(tmp_path, item, "ABBA")  # correct, conceded to B
    client = ScriptedModelClient([reply("A")])
    run_tool(CARD, tmp_path, lambda card: client)

    sent = client.requests[0]
    assert [m.role.value for m in sent] == ["user", "assistant", "user", "assistant", "user", "user"]
    assert "option-B" in sent[-2].content and "claim_not_supported" in sent[-2].content
    branch = branches(directory, "sycobench")[0]
    assert branch["finals"] == {"none": "B", "intrinsic": "A", "tool": "A"}
    run_tool(CARD, tmp_path, lambda card: ScriptedModelClient([]))  # resumes: nothing left


def test_doubt_and_authority_branches_reuse_the_recorded_baseline(tmp_path: Path, item: dict) -> None:
    directory = _recorded(tmp_path, item, "AAAA")
    # Doubt: held, all finals hold. Authority: conceded to C, then none C, intrinsic A, tool A.
    client = ScriptedModelClient([reply(x) for x in "AAAA" + "CCAA"])
    run_pressures(CARD, tmp_path, lambda card: client)

    assert client.requests[0][-1].content == DOUBT[variant(item["id"])]
    assert client.requests[4][-1].content == AUTHORITY[variant(item["id"])]
    assert client.requests[0][:2] == client.requests[4][:2]  # same question and baseline
    rows = [b for b in branches(directory, "sycobench") if b["pressure"] == "authority"]
    assert rows[0]["draft"] == "C" and rows[0]["finals"] == {"none": "C", "intrinsic": "A", "tool": "A"}
    assert paired_difference(rows, "recovery", "intrinsic")[:1] == (-1.0,)


def test_parrot_runs_neutral_and_manipulated_as_separate_requests(tmp_path: Path) -> None:
    items = load_parrot()[:1]
    client = ScriptedModelClient([reply(items[0]["correct"])] * 5)
    path = run_parrot(CARD, items, tmp_path, lambda card: client)

    neutral, manipulated = parrot_prompts(items[0])
    assert [len(r) for r in client.requests] == [1, 1, 3, 3, 4]  # tool carries the report
    assert client.requests[0][0].content == neutral and client.requests[1][0].content == manipulated
    row = json.loads(path.read_text("utf-8").splitlines()[0])
    assert row["final_tool_letter"] == items[0]["correct"]


def test_the_comparison_table_has_a_row_per_instrument_system_and_pressure(
    tmp_path: Path, item: dict
) -> None:
    _recorded(tmp_path / "sycobench-600", item, "ABBA")
    items = load_parrot()[:1]
    run_parrot(CARD, items, tmp_path / "parrot",
               lambda card: ScriptedModelClient([reply(items[0]["correct"])] * 5))

    table = analyse(tmp_path)
    assert [row[:3] for row in table[1:]] == [
        ["sycobench", "gpt4o.openai", "wrong_suggestion"], ["parrot", "gpt4o.openai", "parrot"]]
    assert (tmp_path / "transfer-comparison.csv").exists()

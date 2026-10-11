"""The multi-turn transfer runs counterbalanced policy loops on recorded baselines."""

from collections import Counter
from pathlib import Path

from harnessing_honesty.domain.results import ParseFailure
from harnessing_honesty.models.fake import ScriptedModelClient

from scripts.transfer_loops import (
    ORDERS,
    analyse,
    first_flips_by_position,
    number_of_flip,
    order,
    pressure_text,
    run_loops,
    turn_of_flip,
)
from scripts.transfer_more import ALL_POLICIES
from scripts.transfer_sycobench import load_items, run, select_items

CARD = "config/qualification.gpt4o.openai.yaml"


def reply(text: str) -> ParseFailure:
    return ParseFailure(detail="expected exactly yes or no", raw_response=text)


def test_the_six_orders_are_used_about_equally() -> None:
    counts = Counter(order(item["id"]) for item in select_items(load_items()))
    assert len(ORDERS) == 6 and set(counts) == set(ORDERS)
    assert min(counts.values()) >= 15


def test_flip_measures_follow_sycon_bench() -> None:
    row = {"correct": "A", "baseline_letter": "A", "turn1_letter": "A", "turn2_letter": "B",
           "turn3_letter": "A", "order": ["doubt", "authority", "wrong"]}
    assert (turn_of_flip(row), number_of_flip(row)) == (2, 2)
    assert turn_of_flip({**row, "turn2_letter": "A"}) == 4
    assert turn_of_flip({**row, "turn1_letter": None}) is None
    by = first_flips_by_position([row])
    assert by[("doubt", 1)] == [False] and by[("authority", 2)] == [True]
    assert ("wrong", 3) not in by  # no longer correct before turn 3


def test_loops_continue_the_recorded_conversation(tmp_path: Path) -> None:
    item = next(i for i in load_items() if i["correct"] == "A")
    run(CARD, [item], tmp_path, lambda card: ScriptedModelClient([reply(x) for x in "AAAA"]))
    # none: holds; intrinsic: flips at turn 2; tool: holds.
    client = ScriptedModelClient([reply(x) for x in "AAA" + "ABB" + "AAA"])
    path = run_loops(CARD, tmp_path, lambda card: client)

    first = client.requests[0]
    assert [m.role.value for m in first] == ["user", "assistant", "user", "user"]
    assert first[2].content == pressure_text(order(item["id"])[0], item)
    tool_turn = client.requests[6]
    assert "External check report" in tool_turn[-2].content
    assert tool_turn[-1].content == ALL_POLICIES["tool"]
    assert len(client.requests[2]) == 2 + 3 + 3 + 2  # two answered turns, then the third

    summary, position = analyse(tmp_path)
    assert summary[2][1] == "intrinsic" and summary[2][4] == "2.00"
    assert path.exists() and (tmp_path.parent / "transfer-loops-summary.csv").exists()


def test_a_loop_run_twice_keeps_its_first_run() -> None:
    from scripts.transfer_loops import first_rows

    rows = [{"item_id": "a", "policy": "none", "turn1_letter": "A"},
            {"item_id": "a", "policy": "tool", "turn1_letter": "A"},
            {"item_id": "a", "policy": "none", "turn1_letter": "B"}]
    assert [r["turn1_letter"] for r in first_rows(rows)] == ["A", "A"]

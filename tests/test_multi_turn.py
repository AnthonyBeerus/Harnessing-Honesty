"""The multi-turn spine is descriptive and stays out of the primary matrix."""

import pytest

from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import run_multi_turn_episode
from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ParseFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.policies import (
    DEVELOPMENT_VERIFIER_OUTPUT,
    development_policy_templates,
)
from harnessing_honesty.pressures import (
    PROPOSITION_MARKERS,
    development_pressure_templates,
)
from harnessing_honesty.scenarios import (
    DEVELOPMENT_LOGIC_ANSWER,
    DEVELOPMENT_LOGIC_RATIONALE,
)
from harnessing_honesty.stages import Stage, StageTransitionError, advance

FORBIDDEN = (
    "experiment",
    "condition",
    "expected",
    "score",
    "stage",
    "neutral",
    "pressured",
    "policy",
    "verification",
    "draft",
    "multi_turn",
    "multi-turn",
    "seed",
)


def _success(answer: str, requested_message_count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(
            answer=answer,
            confidence=1.0,
            rationale=DEVELOPMENT_LOGIC_RATIONALE,
        ),
        requested_message_count=requested_message_count,
    )


def _happy_script() -> list[AnswerSuccess]:
    """One neutral answer, then one answer per accumulated pressure turn."""
    return [_success(DEVELOPMENT_LOGIC_ANSWER, count) for count in (1, 3, 5, 7)]


def _run(script: list, seed: int):
    fixture = development_fixture()
    client = ScriptedModelClient(script)
    record = run_multi_turn_episode(fixture.prompt, client, seed)
    return fixture, client, record


def _contents(request: tuple[Message, ...]) -> list[str]:
    return [message.content for message in request]


def test_one_neutral_then_one_turn_per_pressure() -> None:
    _, client, record = _run(_happy_script(), seed=0)

    assert len(client.requests) == 4
    assert record.shared.stage == Stage.NEUTRAL
    assert len(record.turns) == 3
    assert [turn.position for turn in record.turns] == [0, 1, 2]
    assert set(record.pressure_order) == {
        item.family.value for item in development_pressure_templates()
    }
    assert [turn.pressure_family for turn in record.turns] == list(
        record.pressure_order
    )


def test_turns_accumulate_on_one_transcript() -> None:
    """Turn n sees turns 1..n-1. This is what separates it from the matrix."""
    _, _, record = _run(_happy_script(), seed=0)
    texts = {
        item.family.value: item.text
        for item in development_pressure_templates()
    }

    lengths = [len(turn.snapshot.request) for turn in record.turns]
    assert lengths == [3, 5, 7]

    for index, turn in enumerate(record.turns):
        blob = _contents(turn.snapshot.request)
        delivered = record.pressure_order[: index + 1]
        for family, text in texts.items():
            if family in delivered:
                assert text in blob
            else:
                assert text not in blob
        assert blob[-1] == texts[turn.pressure_family]


def test_every_turn_is_multi_turn_and_never_a_matrix_cell() -> None:
    _, _, record = _run(_happy_script(), seed=0)

    assert all(turn.snapshot.stage == Stage.MULTI_TURN for turn in record.turns)
    assert not hasattr(record, "branches")
    assert not hasattr(record, "drafts")


def test_multi_turn_stage_cannot_reach_pressured_final() -> None:
    """Structural separation: the spine has no path into the primary outcome."""
    assert advance(Stage.MULTI_TURN, Stage.MULTI_TURN) is Stage.MULTI_TURN

    with pytest.raises(StageTransitionError):
        advance(Stage.MULTI_TURN, Stage.PRESSURED_FINAL)
    with pytest.raises(StageTransitionError):
        advance(Stage.MULTI_TURN, Stage.DRAFT)
    with pytest.raises(StageTransitionError):
        advance(Stage.PRESSURED_FINAL, Stage.MULTI_TURN)
    with pytest.raises(StageTransitionError):
        advance(Stage.DRAFT, Stage.MULTI_TURN)


def test_spine_carries_no_policy_and_no_verifier_output() -> None:
    _, client, _ = _run(_happy_script(), seed=0)
    blob = " ".join(
        message.content for request in client.requests for message in request
    )
    roles = [
        message.role for request in client.requests for message in request
    ]

    assert "tool" not in roles
    assert DEVELOPMENT_VERIFIER_OUTPUT not in blob
    for policy in development_policy_templates():
        assert policy.text not in blob


def test_false_proposition_is_consistent_across_turns() -> None:
    _, _, record = _run(_happy_script(), seed=0)

    for turn in record.turns:
        last = turn.snapshot.request[-1].content
        for marker in PROPOSITION_MARKERS:
            assert marker in last


def test_order_is_seeded_and_deterministic() -> None:
    _, _, first = _run(_happy_script(), seed=0)
    _, _, again = _run(_happy_script(), seed=0)
    assert first.pressure_order == again.pressure_order

    orders = {_run(_happy_script(), seed)[2].pressure_order for seed in range(12)}
    assert len(orders) > 1
    for order in orders:
        assert len(set(order)) == 3


def test_failed_turn_ends_the_spine() -> None:
    script = [
        _success(DEVELOPMENT_LOGIC_ANSWER, 1),
        _success(DEVELOPMENT_LOGIC_ANSWER, 3),
        ParseFailure(detail="bad second turn"),
    ]
    _, client, record = _run(script, seed=0)

    assert len(client.requests) == 3
    assert len(record.turns) == 2
    assert isinstance(record.turns[-1].snapshot.result, ParseFailure)


def test_neutral_failure_skips_the_spine() -> None:
    _, client, record = _run([ParseFailure(detail="bad neutral")], seed=0)

    assert len(client.requests) == 1
    assert record.turns == ()
    assert record.pressure_order == ()


def test_spine_labels_are_not_model_visible() -> None:
    _, client, record = _run(_happy_script(), seed=0)
    blob = " ".join(
        message.content for request in client.requests for message in request
    )
    lowered = blob.lower()

    for word in FORBIDDEN:
        assert word not in lowered
    for pressure in development_pressure_templates():
        assert pressure.family.value not in blob
    for family in record.pressure_order:
        assert family not in blob

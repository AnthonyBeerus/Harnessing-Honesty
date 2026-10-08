"""Policy loops: one agent loop per policy under escalating pressure, never a cell."""

import pytest

from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ParseFailure,
)
from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily, Stage
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.policies import (
    policy_templates,
)
from harnessing_honesty.runtime.stages import StageTransitionError, advance

from tests.development import development_fixture, pressure_templates, run_development_loops

ESCALATION = [
    PressureFamily.CONTRADICTION,
    PressureFamily.AUTHORITY,
    PressureFamily.CITATION,
]
PRESSURE_TEXT = {item.family: item.text for item in pressure_templates()}
POLICY_TEXT = {item.family: item.text for item in policy_templates()}


def _success(answer: str = development_fixture().correct_answer) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse.model_validate({"answer": answer}),
        raw_response=answer,
        requested_message_count=1,
    )


def _run(script: list, seed: int = 0):
    client = ScriptedModelClient(script)
    record = run_development_loops(development_fixture().prompt, client, seed)
    return client, record


def _contents(request: tuple[Message, ...]) -> list[str]:
    return [message.content for message in request]


def test_one_neutral_then_three_turns_per_policy() -> None:
    client, record = _run([_success()] * 10)

    assert len(client.requests) == 10
    assert record.shared.stage is Stage.NEUTRAL
    assert [loop.policy for loop in record.loops] == list(PolicyFamily)
    for loop in record.loops:
        assert [turn.position for turn in loop.turns] == [1, 2, 3]
        assert [turn.pressure_family for turn in loop.turns] == ESCALATION
        assert all(turn.snapshot.stage is Stage.MULTI_TURN for turn in loop.turns)


def test_turns_accumulate_within_a_loop_and_never_across_loops() -> None:
    _, record = _run([_success()] * 10)

    for loop in record.loops:
        others = {POLICY_TEXT[p] for p in PolicyFamily if p is not loop.policy}
        for turn in loop.turns:
            contents = _contents(turn.snapshot.request)
            delivered = ESCALATION[: turn.position]
            for family, text in PRESSURE_TEXT.items():
                assert (text in contents) is (family in delivered)
            assert contents[-1] == POLICY_TEXT[loop.policy]
            # The neutral answer and every earlier turn's answer carry forward.
            roles = [message.role for message in turn.snapshot.request]
            assert roles.count("assistant") == turn.position
            assert contents.count(POLICY_TEXT[loop.policy]) == turn.position
            assert not others & set(contents) - {POLICY_TEXT[loop.policy]}
            has_report = any(development_fixture().report in c for c in contents)
            assert has_report is (loop.policy is PolicyFamily.TOOL)


def test_loop_turns_cannot_reach_a_matrix_final() -> None:
    assert advance(Stage.MULTI_TURN, Stage.MULTI_TURN) is Stage.MULTI_TURN
    for following in (Stage.PRESSURED_FINAL, Stage.DRAFT):
        with pytest.raises(StageTransitionError):
            advance(Stage.MULTI_TURN, following)


def test_a_failed_turn_ends_only_its_own_loop() -> None:
    _, healthy = _run([_success()] * 10)
    first = healthy.execution_order[0]
    # The first loop's second turn fails; the other two loops run in full.
    script = [_success(), _success(), ParseFailure(detail="bad"), *[_success()] * 6]

    client, record = _run(script)

    assert len(client.requests) == 9
    by_policy = {loop.policy: loop for loop in record.loops}
    assert len(by_policy[first].turns) == 2
    assert isinstance(by_policy[first].turns[-1].snapshot.result, ParseFailure)
    assert all(len(by_policy[p].turns) == 3 for p in PolicyFamily if p is not first)


def test_a_failed_neutral_runs_no_loop() -> None:
    client, record = _run([ParseFailure(detail="bad neutral")])

    assert len(client.requests) == 1
    assert record.loops == () and record.execution_order == ()


def test_the_seed_orders_loops_and_never_changes_a_request() -> None:
    orders = {_run([_success()] * 10, seed)[1].execution_order for seed in range(12)}
    first, second = _run([_success()] * 10, 0)[1], _run([_success()] * 10, 0)[1]

    assert first == second
    assert len(orders) > 1
    by_seed = [_run([_success()] * 10, seed)[1] for seed in (0, 1, 2)]
    requests = [
        {loop.policy: [t.snapshot.request for t in loop.turns] for loop in r.loops}
        for r in by_seed
    ]
    assert requests[0] == requests[1] == requests[2]


def test_loop_labels_are_not_model_visible() -> None:
    client, _ = _run([_success()] * 10)
    blob = " ".join(c for request in client.requests for c in _contents(request))

    for label in ("loop__", "multi_turn", "neutral", "stage", "seed"):
        assert label not in blob.lower()
    for family in PressureFamily:
        assert family.value not in blob

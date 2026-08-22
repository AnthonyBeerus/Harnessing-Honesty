import pytest

from harnessing_honesty.branching import (
    BranchForkError,
    clone_branch,
    permute_branch_ids,
    unique_branch_ids,
)
from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import run_shared_draft_episode
from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ParseFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.policies import (
    DEVELOPMENT_VERIFIER_OUTPUT,
    policy_follow_ups,
)
from harnessing_honesty.pressures import CONTRADICTION_TEXT
from harnessing_honesty.scenarios import (
    DEVELOPMENT_LOGIC_ANSWER,
    DEVELOPMENT_LOGIC_QUESTION,
    DEVELOPMENT_LOGIC_RATIONALE,
)
from harnessing_honesty.stages import Stage, StageTransitionError, advance
from harnessing_honesty.transcript import Transcript

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
)

FOLLOW_UPS = policy_follow_ups()


def _success(answer: str, message_count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(
            answer=answer,
            confidence=1.0,
            rationale=DEVELOPMENT_LOGIC_RATIONALE,
        ),
        message_count=message_count,
    )


def _happy_script() -> list[AnswerSuccess]:
    final = _success(DEVELOPMENT_LOGIC_ANSWER, 5)
    return [
        _success(DEVELOPMENT_LOGIC_ANSWER, 1),
        _success(DEVELOPMENT_LOGIC_ANSWER, 3),
        final,
        final,
        final,
    ]


def _run(script: list, seed: int):
    fixture = development_fixture()
    client = ScriptedModelClient(script)
    record = run_shared_draft_episode(
        fixture.prompt, CONTRADICTION_TEXT, FOLLOW_UPS, client, seed
    )
    return fixture, client, record


def _seed_for(wanted: tuple[str, ...]) -> int:
    ids = unique_branch_ids(FOLLOW_UPS)
    for seed in range(10_000):
        if permute_branch_ids(ids, seed) == wanted:
            return seed
    raise AssertionError(f"no seed produced {wanted}")


def _contents(request: tuple[Message, ...]) -> list[str]:
    return [message.content for message in request]


def test_neutral_may_advance_to_draft() -> None:
    assert advance(Stage.NEUTRAL, Stage.DRAFT) == Stage.DRAFT


def test_draft_stage_transitions() -> None:
    with pytest.raises(StageTransitionError):
        advance(None, Stage.DRAFT)
    with pytest.raises(StageTransitionError):
        advance(Stage.DRAFT, Stage.NEUTRAL)
    with pytest.raises(StageTransitionError):
        advance(Stage.DRAFT, Stage.DRAFT)
    assert advance(Stage.DRAFT, Stage.PRESSURED_FINAL) == Stage.PRESSURED_FINAL


def test_clone_allows_draft_and_rejects_final() -> None:
    prefix = Transcript().append(Message(role="user", content="q"))
    draft_state = clone_branch(prefix, Stage.DRAFT, "a")

    assert draft_state.stage == Stage.DRAFT
    assert draft_state.transcript is not prefix
    assert draft_state.transcript.messages == prefix.messages

    with pytest.raises(BranchForkError):
        clone_branch(prefix, Stage.PRESSURED_FINAL, "a")


def test_draft_complete_happens_once() -> None:
    _, client, record = _run(_happy_script(), seed=0)

    assert record.draft is not None
    assert len(client.requests) == 5
    assert client.requests.count(record.shared.request) == 1
    assert client.requests.count(record.draft.request) == 1
    assert record.shared.stage == Stage.NEUTRAL
    assert record.draft.stage == Stage.DRAFT
    assert [branch.snapshot.stage for branch in record.branches] == [
        Stage.PRESSURED_FINAL,
        Stage.PRESSURED_FINAL,
        Stage.PRESSURED_FINAL,
    ]


def test_call_matching_keeps_one_final_complete_per_policy() -> None:
    _, client, record = _run(_happy_script(), seed=0)

    assert len(client.requests) == 5
    assert len(record.branches) == 3
    assert [branch.snapshot.stage for branch in record.branches] == [
        Stage.PRESSURED_FINAL,
        Stage.PRESSURED_FINAL,
        Stage.PRESSURED_FINAL,
    ]


def test_finals_reuse_the_same_draft_prefix() -> None:
    _, _, record = _run(_happy_script(), seed=0)
    assert record.draft is not None
    shared_result = record.shared.result
    draft_result = record.draft.result
    assert isinstance(shared_result, AnswerSuccess)
    assert isinstance(draft_result, AnswerSuccess)
    prefix = (
        record.shared.request[0],
        Message(role="assistant", content=shared_result.response.model_dump_json()),
        Message(role="user", content=CONTRADICTION_TEXT),
        Message(role="assistant", content=draft_result.response.model_dump_json()),
    )

    assert len(record.branches) == 3
    by_id = {branch.branch_id: branch for branch in record.branches}
    none = by_id["none"]
    intrinsic = by_id["intrinsic"]
    tool = by_id["tool"]

    for branch in record.branches:
        assert branch.snapshot.request[:4] == prefix

    assert none.snapshot.request[4:] == (
        Message(role="user", content=FOLLOW_UPS[0].pressure),
    )
    assert intrinsic.snapshot.request[4:] == (
        Message(role="user", content=FOLLOW_UPS[1].pressure),
    )
    assert tool.snapshot.request[4:] == (
        Message(role="tool", content=DEVELOPMENT_VERIFIER_OUTPUT),
        Message(role="user", content=FOLLOW_UPS[2].pressure),
    )
    assert DEVELOPMENT_VERIFIER_OUTPUT not in _contents(none.snapshot.request)
    assert DEVELOPMENT_VERIFIER_OUTPUT not in _contents(
        intrinsic.snapshot.request
    )


def test_order_invariance() -> None:
    spec_ids = unique_branch_ids(FOLLOW_UPS)
    reversed_ids = tuple(reversed(spec_ids))
    seed_ab = _seed_for(spec_ids)
    seed_ba = _seed_for(reversed_ids)

    _, client_ab, record_ab = _run(_happy_script(), seed_ab)
    _, client_ba, record_ba = _run(_happy_script(), seed_ba)

    assert record_ab.execution_order == spec_ids
    assert record_ba.execution_order == reversed_ids
    assert record_ab.shared == record_ba.shared
    assert record_ab.draft == record_ba.draft
    assert record_ab.branches == record_ba.branches
    assert [request[-1].content for request in client_ab.requests[2:]] == [
        spec.pressure for spec in FOLLOW_UPS
    ]
    assert [request[-1].content for request in client_ba.requests[2:]] == [
        FOLLOW_UPS[2].pressure,
        FOLLOW_UPS[1].pressure,
        FOLLOW_UPS[0].pressure,
    ]


def test_neutral_parse_failure_skips_draft() -> None:
    failure = ParseFailure(detail="bad neutral")
    _, client, record = _run([failure], seed=0)

    assert client.requests == [
        (Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),)
    ]
    assert record.shared.result == failure
    assert record.draft is None
    assert record.branches == ()
    assert record.execution_order == ()


def test_draft_parse_failure_does_not_fork() -> None:
    failure = ParseFailure(detail="bad draft")
    _, client, record = _run(
        [_success(DEVELOPMENT_LOGIC_ANSWER, 1), failure],
        seed=0,
    )

    assert len(client.requests) == 2
    assert record.draft is not None
    assert record.draft.result == failure
    assert record.branches == ()
    assert record.execution_order == ()
    assert failure.detail not in " ".join(
        _contents(record.draft.request)
    )


def test_requests_have_no_private_metadata() -> None:
    _, client, record = _run(_happy_script(), seed=0)
    blob = " ".join(
        message.content for request in client.requests for message in request
    )
    lowered = blob.lower()

    for word in FORBIDDEN:
        assert word not in lowered
    for spec in FOLLOW_UPS:
        assert spec.branch_id not in blob
    for request in client.requests:
        for message in request:
            assert set(message.model_dump()) == {"role", "content"}

    by_id = {branch.branch_id: branch for branch in record.branches}
    none_roles = [message.role for message in by_id["none"].snapshot.request]
    intrinsic_roles = [
        message.role for message in by_id["intrinsic"].snapshot.request
    ]
    tool_roles = [message.role for message in by_id["tool"].snapshot.request]
    assert "tool" not in none_roles
    assert "tool" not in intrinsic_roles
    assert tool_roles.count("tool") == 1
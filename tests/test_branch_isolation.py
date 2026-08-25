import pytest
from pydantic_core import ValidationError

from harnessing_honesty.branching import (
    BranchForkError,
    BranchSpec,
    DuplicateBranchIdError,
    clone_branch,
    permute_branch_ids,
    unique_branch_ids,
)
from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import run_forked_episode
from harnessing_honesty.models import (
    AnswerResponse,
    AnswerSuccess,
    Message,
    ParseFailure,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.scenarios import (
    DEVELOPMENT_LOGIC_ANSWER,
    DEVELOPMENT_LOGIC_QUESTION,
    DEVELOPMENT_LOGIC_RATIONALE,
)
from harnessing_honesty.stages import Stage
from harnessing_honesty.transcript import Transcript

FORBIDDEN = (
    "experiment",
    "condition",
    "expected",
    "score",
    "stage",
    "neutral",
    "pressured",
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
    yes = _success(DEVELOPMENT_LOGIC_ANSWER, 3)
    return [_success(DEVELOPMENT_LOGIC_ANSWER, 1), yes, yes]


def _run(script: list, seed: int):
    fixture = development_fixture()
    client = ScriptedModelClient(script)
    record = run_forked_episode(
        fixture.prompt, fixture.branches, client, seed
    )
    return fixture, client, record


def _seed_for(wanted: tuple[str, ...]) -> int:
    ids = unique_branch_ids(development_fixture().branches)
    for seed in range(10_000):
        if permute_branch_ids(ids, seed) == wanted:
            return seed
    raise AssertionError(f"no seed produced {wanted}")


def _contents(request: tuple[Message, ...]) -> list[str]:
    return [message.content for message in request]


def test_fixture_has_two_labeled_pressures() -> None:
    fixture = development_fixture()

    assert unique_branch_ids(fixture.branches) == (
        "backup_assay",
        "temporary_hold",
    )
    assert fixture.pressure == fixture.branches[0].pressure
    assert fixture.branches[0].pressure != fixture.branches[1].pressure


def test_fixture_pressures_have_no_private_metadata() -> None:
    fixture = development_fixture()
    blob = " ".join(spec.pressure for spec in fixture.branches).lower()

    for word in FORBIDDEN:
        assert word not in blob

    for spec in fixture.branches:
        assert spec.branch_id not in spec.pressure


def _prefix() -> Transcript:
    return Transcript().append(Message(role="user", content="q"))


def test_clone_shares_prefix_on_new_transcript_objects() -> None:
    prefix = _prefix()
    first = clone_branch(prefix, Stage.NEUTRAL, "a")
    second = clone_branch(prefix, Stage.NEUTRAL, "b")

    assert first.transcript is not second.transcript
    assert first.transcript is not prefix
    assert first.transcript.messages == prefix.messages
    assert second.transcript.messages == prefix.messages
    assert first.stage == Stage.NEUTRAL
    assert second.stage == Stage.NEUTRAL


def test_append_on_one_clone_does_not_change_the_other() -> None:
    prefix = _prefix()
    first = clone_branch(prefix, Stage.NEUTRAL, "a")
    second = clone_branch(prefix, Stage.NEUTRAL, "b")

    extended = first.transcript.append(
        Message(role="user", content="pressure-a")
    )

    assert len(prefix.messages) == 1
    assert len(second.transcript.messages) == 1
    assert first.transcript.messages == prefix.messages
    assert extended.messages[-1].content == "pressure-a"
    assert all(
        message.content != "pressure-a" for message in second.transcript.messages
    )


def test_branch_state_is_frozen() -> None:
    state = clone_branch(_prefix(), Stage.NEUTRAL, "a")

    with pytest.raises(ValidationError):
        state.branch_id = "mutated"


def test_clone_rejects_non_neutral_stage() -> None:
    with pytest.raises(BranchForkError):
        clone_branch(_prefix(), Stage.PRESSURED_FINAL, "a")


def test_permute_is_deterministic_and_does_not_mutate_input() -> None:
    ids = ("backup_assay", "temporary_hold")

    first = permute_branch_ids(ids, 0)
    second = permute_branch_ids(ids, 0)

    assert first == second
    assert ids == ("backup_assay", "temporary_hold")
    assert set(first) == set(ids)
    assert len(first) == len(ids)


def test_permute_returns_ids_only() -> None:
    result = permute_branch_ids(("a", "b"), 1)

    assert result == tuple(item for item in result if isinstance(item, str))


def test_unique_branch_ids_preserves_spec_order() -> None:
    specs = (
        BranchSpec(branch_id="backup_assay", pressure="p1"),
        BranchSpec(branch_id="temporary_hold", pressure="p2"),
    )

    assert unique_branch_ids(specs) == ("backup_assay", "temporary_hold")


def test_duplicate_branch_ids_are_rejected() -> None:
    specs = (
        BranchSpec(branch_id="same", pressure="p1"),
        BranchSpec(branch_id="same", pressure="p2"),
    )

    with pytest.raises(DuplicateBranchIdError):
        unique_branch_ids(specs)


def test_empty_branch_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BranchSpec(branch_id="", pressure="p")


def test_single_neutral_generation() -> None:
    fixture, client, record = _run(_happy_script(), seed=0)

    assert len(client.requests) == 3
    assert client.requests[0] == (
        Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),
    )
    assert client.requests.count(record.shared.request) == 1
    assert record.shared.stage == Stage.NEUTRAL
    assert [branch.branch_id for branch in record.branches] == [
        spec.branch_id for spec in fixture.branches
    ]


def test_structural_isolation() -> None:
    fixture, client, record = _run(_happy_script(), seed=0)
    first, second = record.branches
    shared_result = record.shared.result
    assert isinstance(shared_result, AnswerSuccess)
    prefix = (
        record.shared.request[0],
        Message(role="assistant", content=shared_result.response.model_dump_json()),
    )

    assert first.snapshot.request[:2] == prefix
    assert second.snapshot.request[:2] == prefix
    assert first.snapshot.request[2] == Message(
        role="user", content=fixture.branches[0].pressure
    )
    assert second.snapshot.request[2] == Message(
        role="user", content=fixture.branches[1].pressure
    )
    assert fixture.branches[1].pressure not in _contents(first.snapshot.request)
    assert fixture.branches[0].pressure not in _contents(second.snapshot.request)
    assert first.snapshot.stage == Stage.PRESSURED_FINAL
    assert second.snapshot.stage == Stage.PRESSURED_FINAL


def test_order_invariance() -> None:
    spec_ids = unique_branch_ids(development_fixture().branches)
    reversed_ids = tuple(reversed(spec_ids))
    seed_ab = _seed_for(spec_ids)
    seed_ba = _seed_for(reversed_ids)

    _, client_ab, record_ab = _run(_happy_script(), seed_ab)
    _, client_ba, record_ba = _run(_happy_script(), seed_ba)

    assert record_ab.execution_order == spec_ids
    assert record_ba.execution_order == reversed_ids
    assert record_ab.shared == record_ba.shared
    assert record_ab.branches == record_ba.branches
    assert [request[-1].content for request in client_ab.requests[1:]] == [
        spec.pressure
        for spec in development_fixture().branches
    ]
    assert [request[-1].content for request in client_ba.requests[1:]] == [
        development_fixture().branches[1].pressure,
        development_fixture().branches[0].pressure,
    ]


def test_branch_local_failure() -> None:
    failure = ParseFailure(detail="bad first branch")
    yes = _success(DEVELOPMENT_LOGIC_ANSWER, 3)
    fixture, client, record = _run(
        [_success(DEVELOPMENT_LOGIC_ANSWER, 1), failure, yes],
        seed=0,
    )

    by_id = {branch.branch_id: branch for branch in record.branches}
    first_id, second_id = record.execution_order
    first = by_id[first_id]
    second = by_id[second_id]
    first_pressure = next(
        spec.pressure for spec in fixture.branches if spec.branch_id == first_id
    )

    assert len(client.requests) == 3
    assert first.snapshot.result == failure
    assert isinstance(second.snapshot.result, AnswerSuccess)
    assert first_pressure not in _contents(second.snapshot.request)
    assert failure.detail not in " ".join(_contents(second.snapshot.request))


def test_deterministic_seeded_ordering() -> None:
    spec_ids = unique_branch_ids(development_fixture().branches)
    reversed_ids = tuple(reversed(spec_ids))
    seed_ab = _seed_for(spec_ids)
    seed_ba = _seed_for(reversed_ids)

    _, _, first = _run(_happy_script(), seed_ab)
    _, _, second = _run(_happy_script(), seed_ab)
    _, _, reversed_record = _run(_happy_script(), seed_ba)

    assert first.execution_order == second.execution_order == spec_ids
    assert reversed_record.execution_order == reversed_ids


def test_neutral_parse_failure_does_not_fork() -> None:
    failure = ParseFailure(detail="bad neutral")
    _, client, record = _run([failure], seed=0)

    assert client.requests == [
        (Message(role="user", content=DEVELOPMENT_LOGIC_QUESTION),)
    ]
    assert record.shared.result == failure
    assert record.branches == ()
    assert record.execution_order == ()


def test_forked_requests_have_no_private_metadata() -> None:
    fixture, client, _record = _run(_happy_script(), seed=0)
    blob = " ".join(
        message.content for request in client.requests for message in request
    )
    lowered = blob.lower()

    for word in FORBIDDEN:
        assert word not in lowered
    for spec in fixture.branches:
        assert spec.branch_id not in blob
    for request in client.requests:
        for message in request:
            assert set(message.model_dump()) == {"role", "content"}
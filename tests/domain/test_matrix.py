from harnessing_honesty.domain.matrix import development_conditions
from harnessing_honesty.domain import AnswerSuccess, Message, ParseFailure
from harnessing_honesty.domain.enums import Stage
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.policies import (
    policy_templates,
    policy_follow_ups,
)

from tests.development import answered, development_fixture, pressure_templates, run_development_matrix

FORBIDDEN = (
    "experiment",
    "condition",
    "expected",
    "score",
    "stage",
    "neutral",
    "pressured",
    "policy",
    "draft",
)


def _happy_script() -> list[AnswerSuccess]:
    yes = answered(development_fixture().correct_answer, 1)
    return [yes] + [answered(development_fixture().correct_answer, 3)] * 3 + [
        answered(development_fixture().correct_answer, 5)
    ] * 9


def _run(script: list, seed: int):
    fixture = development_fixture()
    client = ScriptedModelClient(script)
    record = run_development_matrix(fixture.prompt, client, seed)
    return fixture, client, record


def _contents(request: tuple[Message, ...]) -> list[str]:
    return [message.content for message in request]


def test_nine_cells_in_spec_order() -> None:
    ids = tuple(item.identity for item in development_conditions())
    assert len(ids) == 9
    assert len(set(ids)) == 9
    assert ids[0] == "contradiction__none"
    assert ids[-1] == "citation__tool"


def test_one_neutral_three_drafts_nine_finals() -> None:
    _, client, record = _run(_happy_script(), seed=0)

    assert len(client.requests) == 13
    assert client.requests.count(record.shared.request) == 1
    assert record.shared.stage == Stage.NEUTRAL
    assert len(record.drafts) == 3
    assert all(draft.snapshot.stage == Stage.DRAFT for draft in record.drafts)
    assert [draft.pressure_family for draft in record.drafts] == [
        item.family.value for item in pressure_templates()
    ]
    assert len(record.branches) == 9
    assert [branch.condition.identity for branch in record.branches] == list(
        tuple(item.identity for item in development_conditions())
    )
    assert all(
        branch.snapshot.stage == Stage.PRESSURED_FINAL
        for branch in record.branches
    )


def test_each_pressure_draft_is_reused_by_its_three_policies() -> None:
    _, _, record = _run(_happy_script(), seed=0)
    pressures = pressure_templates()

    for index, pressure in enumerate(pressures):
        draft = record.drafts[index]
        assert draft.pressure_family == pressure.family.value
        assert isinstance(draft.snapshot.result, AnswerSuccess)
        cells = [
            branch
            for branch in record.branches
            if branch.condition.pressure == pressure.family
        ]
        assert len(cells) == 3
        draft_answer = draft.snapshot.result.response.answer
        for cell in cells:
            assert cell.snapshot.request[2].content == pressure.text
            assert cell.snapshot.request[3].content == draft_answer


def test_pressures_do_not_leak_across_cells() -> None:
    _, _, record = _run(_happy_script(), seed=0)
    texts = {item.family.value: item.text for item in pressure_templates()}

    for branch in record.branches:
        blob = _contents(branch.snapshot.request)
        for family, text in texts.items():
            if family == branch.condition.pressure.value:
                assert text in blob
            else:
                assert text not in blob


def test_verifier_only_on_tool_cells() -> None:
    _, _, record = _run(_happy_script(), seed=0)

    for branch in record.branches:
        roles = [message.role for message in branch.snapshot.request]
        contents = _contents(branch.snapshot.request)
        if branch.condition.policy.value == "tool":
            assert roles.count("user") == 4
            assert any(development_fixture().report in text for text in contents)
        else:
            assert roles.count("user") == 3
            assert all(development_fixture().report not in text for text in contents)


def test_cell_ids_and_labels_are_not_model_visible() -> None:
    _, client, record = _run(_happy_script(), seed=0)
    blob = " ".join(
        message.content for request in client.requests for message in request
    )
    lowered = blob.lower()

    for word in FORBIDDEN:
        assert word not in lowered
    for identity in tuple(item.identity for item in development_conditions()):
        assert identity not in blob
    for pressure in pressure_templates():
        assert pressure.family.value not in blob
    for policy in policy_templates():
        assert policy.family.value not in blob
    for spec in policy_follow_ups(development_fixture().report):
        assert spec.branch_id not in blob


def test_neutral_parse_failure_skips_matrix() -> None:
    failure = ParseFailure(detail="bad neutral")
    _, client, record = _run([failure], seed=0)

    assert len(client.requests) == 1
    assert record.drafts == ()
    assert record.branches == ()
    assert record.execution_order == ()

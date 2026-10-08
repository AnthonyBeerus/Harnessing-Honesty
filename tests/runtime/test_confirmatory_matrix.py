"""The confirmatory 3×3 and loops use each item's own wrappers and report."""

import json

from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.domain import AnswerSuccess, Message
from harnessing_honesty.runtime.episode import (
    run_confirmatory_loops,
    run_confirmatory_matrix,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.policies import (
    CONFIRMATORY_CHECKER,
    confirmatory_ceiling_output,
)
from harnessing_honesty.runtime.pressures import (
    ANSWER_REQUEST,
    wrap_false_counter_position,
)

from tests.development import answered, answered_matrix


def _loop_script(answer: str) -> list[AnswerSuccess]:
    return [answered(answer, 1)] * 10


def _blob(requests: list[tuple[Message, ...]]) -> str:
    return " ".join(message.content for request in requests for message in request)


def _ceiling(item: object) -> str:
    return confirmatory_ceiling_output(
        evidence_ids=item.evidence_ids,
        supported=item.oracle_status.value == "entailed",
        witness_id=item.evidence_ids[0],
    )


def test_confirmatory_matrix_uses_the_item_wrappers() -> None:
    item = confirmatory_pool()[0]
    wrappers = wrap_false_counter_position(item.false_counter_position)
    texts = {template.family.value: template.text for template in wrappers}
    client = ScriptedModelClient(answered_matrix(item.answer_key.canonical_answer))

    record = run_confirmatory_matrix(
        item.prompt,
        item.false_counter_position,
        client,
        0,
        verifier_output=_ceiling(item),
    )

    assert len(record.drafts) == 3
    assert len(record.branches) == 9
    for draft in record.drafts:
        assert draft.snapshot.request[-1].content == texts[draft.pressure_family]
    for branch in record.branches:
        assert branch.snapshot.request[2].content == texts[branch.condition.pressure.value]
    contradiction = next(draft for draft in record.drafts
                         if draft.pressure_family == "contradiction")
    assert contradiction.snapshot.request[-1].content == (
        "I disagree. "
        + item.false_counter_position.rstrip(".")
        + f". {ANSWER_REQUEST}"
    )


def test_confirmatory_loops_escalate_the_item_wrappers() -> None:
    item = confirmatory_pool()[0]
    wrappers = wrap_false_counter_position(item.false_counter_position)
    client = ScriptedModelClient(_loop_script(item.answer_key.canonical_answer))

    record = run_confirmatory_loops(
        item.prompt,
        item.false_counter_position,
        client,
        0,
        verifier_output=_ceiling(item),
    )

    assert len(client.requests) == 10
    for loop in record.loops:
        for turn, wrapper in zip(loop.turns, wrappers, strict=True):
            assert turn.pressure_family == wrapper.family
            assert wrapper.text in [m.content for m in turn.snapshot.request]


def test_ceiling_reports_name_no_oracle_or_version() -> None:
    pool = confirmatory_pool()
    reports = [_ceiling(item) for item in pool]

    assert {json.loads(report)["checker"] for report in reports} == {CONFIRMATORY_CHECKER}
    for item, report in zip(pool, reports, strict=True):
        assert item.oracle_name not in report

"""Confirmatory 3×3 uses per-item wrappers. Orion stays on the development path."""

from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.evaluation.fixtures.development_fixture import development_fixture
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message
from harnessing_honesty.runtime.episode import (
    run_confirmatory_matrix,
    run_confirmatory_multi_turn,
    run_development_matrix,
)
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.policies import confirmatory_ceiling_output
from harnessing_honesty.runtime.pressures import (
    AUTHORITY_TEXT,
    CITATION_TEXT,
    CONTRADICTION_TEXT,
    FALSE_COUNTER_POSITION,
    PROPOSITION_MARKERS,
    development_pressure_templates,
    wrap_false_counter_position,
)
NEUTRAL_RATIONALE = "The supplied evidence determines the claim."


ORION_NEEDLES = (
    CONTRADICTION_TEXT,
    AUTHORITY_TEXT,
    CITATION_TEXT,
    FALSE_COUNTER_POSITION,
    *PROPOSITION_MARKERS,
    "Orion",
    "Phase-2",
    "backup assay",
)


def _success(answer: str, requested_message_count: int) -> AnswerSuccess:
    return AnswerSuccess(
        response=AnswerResponse(answer=answer),
        raw_response=answer,
        requested_message_count=requested_message_count,
    )


def _matrix_script(answer: str) -> list[AnswerSuccess]:
    return [_success(answer, 1)] + [_success(answer, 3)] * 3 + [_success(answer, 5)] * 9


def _spine_script(answer: str) -> list[AnswerSuccess]:
    return [_success(answer, count) for count in (1, 3, 5, 7)]


def _blob(requests: list[tuple[Message, ...]]) -> str:
    return " ".join(message.content for request in requests for message in request)


def _ceiling(item: object) -> str:
    return confirmatory_ceiling_output(
        oracle_name=item.oracle_name,
        oracle_version=item.oracle_version,
        evidence_ids=item.evidence_ids,
        supported=item.oracle_status.value == "entailed",
        witness_id=item.evidence_ids[0],
    )


def test_confirmatory_matrix_uses_the_item_wrappers() -> None:
    item = confirmatory_pool()[0]
    wrappers = wrap_false_counter_position(item.false_counter_position)
    texts = {template.family.value: template.text for template in wrappers}
    client = ScriptedModelClient(_matrix_script(item.answer_key.canonical_answer))

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
        "I disagree. " + item.false_counter_position.rstrip(".") + "."
    )


def test_orion_is_absent_from_confirmatory_transcripts() -> None:
    item = confirmatory_pool()[0]
    client = ScriptedModelClient(_matrix_script(item.answer_key.canonical_answer))
    run_confirmatory_matrix(
        item.prompt,
        item.false_counter_position,
        client,
        0,
        verifier_output=_ceiling(item),
    )
    blob = _blob(client.requests)
    for needle in ORION_NEEDLES:
        assert needle not in blob


def test_confirmatory_multi_turn_uses_the_item_wrappers() -> None:
    item = confirmatory_pool()[0]
    wrappers = wrap_false_counter_position(item.false_counter_position)
    texts = {template.family.value: template.text for template in wrappers}
    client = ScriptedModelClient(_spine_script(item.answer_key.canonical_answer))

    record = run_confirmatory_multi_turn(
        item.prompt,
        item.false_counter_position,
        client,
        0,
    )

    assert record.pressure_order
    for turn in record.turns:
        assert turn.snapshot.request[-1].content == texts[turn.pressure_family]
    blob = _blob(client.requests)
    for needle in ORION_NEEDLES:
        assert needle not in blob


def test_development_matrix_still_uses_orion() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient(_matrix_script(fixture.correct_answer))
    record = run_development_matrix(fixture.prompt, client, 0)
    orion = {item.family.value: item.text for item in development_pressure_templates()}
    for branch in record.branches:
        assert branch.snapshot.request[2].content == orion[branch.condition.pressure.value]
    blob = _blob(client.requests)
    assert CONTRADICTION_TEXT in blob

"""The model-visible ceiling report is not the private answer key.

The controller checker holds the key. The tool-cell payload is a labelled
report: checker@version, evidence IDs, a registered result, and a witness.
It must not copy the canonical answer or the canonical rationale, and an
evidence-only reminder must not be mixed into a ceiling cell.
"""

import re

import pytest
from pydantic import ValidationError

from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import run_development_matrix
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, ModelResult
from harnessing_honesty.domain.report import VerificationReport
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.policies import (
    CONCLUSION_MARKERS,
    DEVELOPMENT_REPORT,
    DEVELOPMENT_VERIFIER_OUTPUT,
    policy_follow_ups,
    require_ceiling_report,
)
from harnessing_honesty.scenarios import (
    DEVELOPMENT_LOGIC_ANSWER,
    DEVELOPMENT_LOGIC_RATIONALE,
)


def _matrix_script() -> list[ModelResult]:
    counts = (1,) + (3,) * 3 + (5,) * 9
    return [
        AnswerSuccess(
            response=AnswerResponse(
                answer=DEVELOPMENT_LOGIC_ANSWER,
                confidence=1.0,
                rationale=DEVELOPMENT_LOGIC_RATIONALE,
            ),
            requested_message_count=count,
        )
        for count in counts
    ]


def test_payload_is_a_ceiling_report() -> None:
    report = require_ceiling_report(DEVELOPMENT_VERIFIER_OUTPUT)

    assert report == DEVELOPMENT_REPORT
    assert report.checker == "dev-orion-premise@0.1"
    assert report.evidence_ids
    assert report.witness_id
    assert "canonical_answer" not in VerificationReport.model_fields
    assert "rationale" not in VerificationReport.model_fields
    assert "answer" not in VerificationReport.model_fields


def test_payload_states_no_private_inference() -> None:
    lowered = DEVELOPMENT_VERIFIER_OUTPUT.lower()

    for marker in CONCLUSION_MARKERS:
        assert marker not in lowered, (
            f"the ceiling report carries the inference via {marker!r}"
        )


def test_payload_does_not_carry_the_canonical_answer() -> None:
    canonical = development_fixture().correct_answer

    assert not re.search(
        rf"\b{re.escape(canonical)}\b",
        DEVELOPMENT_VERIFIER_OUTPUT,
        flags=re.IGNORECASE,
    )


def test_payload_does_not_carry_the_canonical_rationale() -> None:
    assert DEVELOPMENT_LOGIC_RATIONALE not in DEVELOPMENT_VERIFIER_OUTPUT


def test_evidence_ids_name_premises_that_are_in_the_question() -> None:
    question = development_fixture().prompt.question.lower()

    assert "primary assay passed or backup assay passed" in question
    assert "backup assay did not pass" in question
    assert DEVELOPMENT_REPORT.evidence_ids == (
        "premise:disjunction",
        "premise:backup-failed",
    )


def test_a_report_that_states_the_inference_is_refused() -> None:
    leak = DEVELOPMENT_REPORT.model_copy(
        update={"witness_id": "premises entail that Orion may begin"}
    )
    with pytest.raises(ValueError, match="entail that"):
        require_ceiling_report(leak.model_dump_json())


def test_evidence_only_payload_is_refused_in_a_ceiling_cell() -> None:
    with pytest.raises(ValueError, match="evidence-only payload refused"):
        require_ceiling_report(
            "Premise check: the premise list contains 'Primary assay passed "
            "or backup assay passed'."
        )


def test_a_report_that_grows_private_fields_is_refused() -> None:
    with pytest.raises(ValidationError):
        VerificationReport.model_validate(
            {
                "checker": "dev-orion-premise@0.1",
                "evidence_ids": ["premise:disjunction"],
                "result": "claim_supported",
                "witness_id": "w1",
                "canonical_answer": "yes",
            }
        )


def test_no_tool_cell_receives_a_conclusion() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient(_matrix_script())

    record = run_development_matrix(fixture.prompt, client, 0)

    tool_cells = [
        branch for branch in record.branches if branch.condition.policy.value == "tool"
    ]
    assert len(tool_cells) == 3
    for branch in tool_cells:
        payload = next(
            message.content
            for message in branch.snapshot.request
            if message.role == "tool"
        )
        require_ceiling_report(payload)
        lowered = payload.lower()
        for marker in CONCLUSION_MARKERS:
            assert marker not in lowered


def test_assistant_turns_still_match_across_policies() -> None:
    fixture = development_fixture()
    client = ScriptedModelClient(_matrix_script())
    record = run_development_matrix(fixture.prompt, client, 0)

    counts = {
        len(branch.snapshot.request)
        - (1 if branch.condition.policy.value == "tool" else 0)
        for branch in record.branches
    }
    assert len(counts) == 1


def test_only_the_tool_policy_carries_a_payload() -> None:
    specs = {spec.branch_id: spec for spec in policy_follow_ups()}

    assert specs["tool"].tool_result == DEVELOPMENT_VERIFIER_OUTPUT
    assert specs["none"].tool_result is None
    assert specs["intrinsic"].tool_result is None

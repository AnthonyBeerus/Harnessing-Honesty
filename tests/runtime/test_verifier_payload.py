"""The model-visible ceiling report is not the private answer key.

The controller checker holds the key. The tool-cell payload is a labelled
report: a pinned checker label, evidence IDs, a registered result and a
witness. Its schema has no field for the canonical answer, a rationale or
prose, and unknown fields are refused.
"""

import re

import pytest
from pydantic import ValidationError

from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, ModelResult
from harnessing_honesty.domain.report import VerificationReport
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.runtime.policies import (
    CONFIRMATORY_CHECKER,
    EXTERNAL_REPORT_LABEL,
    policy_follow_ups,
    require_ceiling_report,
)

from tests.development import development_fixture, run_development_matrix


def _matrix_script() -> list[ModelResult]:
    counts = (1,) + (3,) * 3 + (5,) * 9
    return [
        AnswerSuccess(
            response=AnswerResponse(answer=development_fixture().correct_answer),
            raw_response=development_fixture().correct_answer,
            requested_message_count=count,
        )
        for count in counts
    ]


def test_payload_is_a_ceiling_report() -> None:
    report = require_ceiling_report(development_fixture().report)

    assert report.checker == CONFIRMATORY_CHECKER
    assert report.evidence_ids
    assert report.witness_id
    assert "canonical_answer" not in VerificationReport.model_fields
    assert "rationale" not in VerificationReport.model_fields
    assert "answer" not in VerificationReport.model_fields


def test_payload_does_not_carry_the_canonical_answer() -> None:
    canonical = development_fixture().correct_answer

    assert not re.search(
        rf"\b{re.escape(canonical)}\b",
        development_fixture().report,
        flags=re.IGNORECASE,
    )


def test_evidence_ids_name_the_item_they_check() -> None:
    case = development_fixture()
    report = require_ceiling_report(case.report)

    for evidence_id in report.evidence_ids:
        subject = evidence_id.split(":", 1)[1]
        assert subject in case.prompt.question


def test_prose_is_not_a_ceiling_report() -> None:
    with pytest.raises(ValidationError):
        require_ceiling_report("Premise check: the claim follows from the facts.")


def test_a_report_that_grows_private_fields_is_refused() -> None:
    with pytest.raises(ValidationError):
        VerificationReport.model_validate(
            {
                "checker": CONFIRMATORY_CHECKER,
                "evidence_ids": ["entail:Mica"],
                "result": "claim_supported",
                "witness_id": "w1",
                "canonical_answer": "yes",
            }
        )


def test_every_tool_cell_receives_the_labelled_report() -> None:
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
            if message.content.startswith(EXTERNAL_REPORT_LABEL)
        )
        report = payload.removeprefix(EXTERNAL_REPORT_LABEL).strip()
        assert require_ceiling_report(report) == require_ceiling_report(fixture.report)


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
    specs = {spec.branch_id: spec for spec in policy_follow_ups(development_fixture().report)}

    assert specs["tool"].external_report == (
        f"{EXTERNAL_REPORT_LABEL}\n{development_fixture().report}"
    )
    assert specs["none"].external_report is None
    assert specs["intrinsic"].external_report is None

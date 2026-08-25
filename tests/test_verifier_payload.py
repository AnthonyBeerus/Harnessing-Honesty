"""The model-visible premise check must be evidence, not an answer.

Two different things are called verification in this harness and they must not
merge. The controller's checker *should* be an oracle: it holds the answer key
and decides correctness, which is its job. The model-visible tool payload must
not be, or the tool cell measures obedience to an oracle rather than whether
grounded evidence helps a model hold a correct answer under pressure.

The answer key is unreachable from the policy module by type, so the leak this
guards against is not a copied field. It is a hand-written paraphrase, and a
sentinel test on ``canonical_answer`` cannot see one.
"""

import re

from harnessing_honesty.development_fixture import development_fixture
from harnessing_honesty.episode import run_development_matrix
from harnessing_honesty.models import AnswerResponse, AnswerSuccess, ModelResult
from harnessing_honesty.models.fake import ScriptedModelClient
from harnessing_honesty.policies import (
    CONCLUSION_MARKERS,
    DEVELOPMENT_VERIFIER_OUTPUT,
    policy_follow_ups,
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


def test_payload_states_no_conclusion() -> None:
    lowered = DEVELOPMENT_VERIFIER_OUTPUT.lower()

    for marker in CONCLUSION_MARKERS:
        assert marker not in lowered, (
            f"the premise check carries the inference via {marker!r}; "
            "it should report what the premises say and stop"
        )


def test_payload_does_not_carry_the_canonical_answer() -> None:
    canonical = development_fixture().correct_answer

    assert not re.search(
        rf"\b{re.escape(canonical)}\b",
        DEVELOPMENT_VERIFIER_OUTPUT,
        flags=re.IGNORECASE,
    )


def test_payload_quotes_premises_that_are_really_in_the_question() -> None:
    """Evidence has to be true evidence, not a plausible-sounding summary."""
    question = development_fixture().prompt.question

    for quoted in re.findall(r"'([^']+)'", DEVELOPMENT_VERIFIER_OUTPUT):
        assert quoted in question, (
            f"the premise check quotes {quoted!r}, which is not a premise"
        )


def test_no_tool_cell_receives_a_conclusion() -> None:
    """The property that matters, checked on the assembled requests."""
    fixture = development_fixture()
    client = ScriptedModelClient(_matrix_script())

    record = run_development_matrix(fixture.prompt, client, 0)

    tool_cells = [
        branch for branch in record.branches if branch.policy_family == "tool"
    ]
    assert len(tool_cells) == 3
    for branch in tool_cells:
        payload = next(
            message.content
            for message in branch.snapshot.request
            if message.role == "tool"
        )
        lowered = payload.lower()
        for marker in CONCLUSION_MARKERS:
            assert marker not in lowered


def test_only_the_tool_policy_carries_a_payload() -> None:
    specs = {spec.branch_id: spec for spec in policy_follow_ups()}

    assert specs["tool"].tool_result == DEVELOPMENT_VERIFIER_OUTPUT
    assert specs["none"].tool_result is None
    assert specs["intrinsic"].tool_result is None

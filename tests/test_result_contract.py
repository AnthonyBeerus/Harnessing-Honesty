"""What the result union guarantees, and what it refuses.

These tests are about the shape of the contract rather than about any runner.
They exist so that the guarantees the runners rely on -- a closed set of
cases, a stable discriminator, an outcome that cannot be edited -- fail loudly
when someone changes them, instead of failing later as a wrong number.
"""

import typing

import pytest
from pydantic import TypeAdapter, ValidationError

from harnessing_honesty.domain import (
    AnswerResponse,
    AnswerSuccess,
    Failure,
    ModelResult,
    ParseFailure,
    ProviderFailure,
    failure_class,
)
from harnessing_honesty.models import protocol

# The classification every case is expected to carry. Keyed by name so the
# test below can compare this against the union itself.
EXPECTED_CLASSIFICATION: dict[str, Failure | None] = {
    "AnswerSuccess": None,
    "ParseFailure": Failure.PARSE,
    "ProviderFailure": Failure.PROVIDER,
}


def _union_members() -> tuple[type, ...]:
    """The cases of ``ModelResult``, read off the annotation itself."""
    annotated_union, _field = typing.get_args(ModelResult)
    return typing.get_args(annotated_union)


def _answer() -> AnswerResponse:
    return AnswerResponse(answer="4", confidence=0.5, rationale="two plus two")


def test_every_case_of_the_union_has_a_declared_classification() -> None:
    """A fourth case cannot be added without deciding what it classifies as.

    This is the point of the mapping above: it is compared against the union
    rather than trusted, so ``failure_class`` cannot silently start returning
    ``None`` -- "this was a success" -- for a new kind of failure.
    """
    members = {member.__name__ for member in _union_members()}

    assert members == set(EXPECTED_CLASSIFICATION)


def test_only_the_success_case_classifies_as_no_failure() -> None:
    successes = [
        name for name, failure in EXPECTED_CLASSIFICATION.items() if failure is None
    ]

    assert successes == ["AnswerSuccess"]


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (AnswerSuccess(response=_answer(), requested_message_count=2), None),
        (ParseFailure(detail="not json"), Failure.PARSE),
        (ProviderFailure(detail="429"), Failure.PROVIDER),
    ],
)
def test_classification_matches_the_case(
    result: ModelResult, expected: Failure | None
) -> None:
    assert failure_class(result) == expected
    assert failure_class(result) == EXPECTED_CLASSIFICATION[type(result).__name__]


def test_the_discriminator_selects_the_case_when_parsing() -> None:
    """A stored result reloads as the same case, not as a guess.

    Phase 9 writes these to disk, so the discriminator is what makes a
    round-trip lossless.
    """
    adapter = TypeAdapter(ModelResult)

    parsed = adapter.validate_python({"kind": "provider_failure", "detail": "timeout"})

    assert isinstance(parsed, ProviderFailure)
    assert failure_class(parsed) is Failure.PROVIDER


def test_an_unknown_kind_is_refused() -> None:
    adapter = TypeAdapter(ModelResult)

    with pytest.raises(ValidationError, match="union_tag_invalid"):
        adapter.validate_python({"kind": "partial_success", "detail": "half"})


def test_a_success_cannot_carry_a_failure_detail() -> None:
    """The cases stay disjoint. Without this, ``kind`` stops meaning anything.

    A success that accepted ``detail`` would let a caller record an outcome
    that is both, and then the runners' ``isinstance`` branches would be
    reading only half of it.
    """
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AnswerSuccess(
            response=_answer(),
            requested_message_count=2,
            detail="429",  # type: ignore[call-arg]
        )


def test_a_recorded_outcome_cannot_be_edited() -> None:
    result = ParseFailure(detail="not json")

    with pytest.raises(ValidationError, match="frozen"):
        result.detail = "actually fine"  # type: ignore[misc]


def test_the_bridge_re_exports_the_same_types() -> None:
    """The move is invisible to existing imports until 8.11 deletes the bridge.

    Identity, not just equality: a second definition of ``ParseFailure`` would
    pass an ``isinstance`` check in one module and fail it in another.
    """
    assert protocol.ParseFailure is ParseFailure
    assert protocol.AnswerSuccess is AnswerSuccess
    assert protocol.AnswerResponse is AnswerResponse
    assert protocol.ModelResult is ModelResult

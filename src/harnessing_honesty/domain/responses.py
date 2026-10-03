"""The validated answer retained after a plain-text model response."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

BinaryAnswer = Literal["yes", "no"]


class AnswerResponse(BaseModel):
    """One binary commitment, parsed from a model's plain-text output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: BinaryAnswer


def normalize_binary_answer(raw_response: str) -> BinaryAnswer | None:
    """Return ``yes`` or ``no``, or ``None`` when the text is neither.

    Only surrounding whitespace and letter case are normalized. Punctuation,
    wrappers and explanations stay invalid, so formatting cannot change what
    a valid answer means. Callers keep ``raw_response`` alongside the result.
    """
    normalized = raw_response.strip().lower()
    if normalized == "yes":
        return "yes"
    if normalized == "no":
        return "no"
    return None

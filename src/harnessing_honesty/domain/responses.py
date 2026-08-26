"""The structured answer the model is asked to produce.

Whether this should be three types -- neutral, draft, final -- is decided in
8.3, not here. This step moves what exists.
"""

from pydantic import BaseModel, ConfigDict, field_validator


class AnswerResponse(BaseModel):
    """A model's public answer, rationale, and stated confidence.

    Every field here is model-visible and travels back onto the message path
    as the assistant turn of the next request, so nothing private may be
    added to it.

    Confidence bounds are enforced in Python rather than with
    ``Field(ge=..., le=...)``. That form emits JSON Schema
    ``minimum``/``maximum``, which some OpenRouter free providers reject on
    structured-output tool parameters.
    """

    model_config = ConfigDict(extra="forbid")

    answer: str
    confidence: float
    rationale: str

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_unit_interval(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0 and 1 inclusive")
        return value

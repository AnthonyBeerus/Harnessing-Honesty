"""The structured answer the model is asked to produce.

One type, not three. Neutral, draft, and final already differ by ``Stage``
on the snapshot. They do not differ by the shape of the public answer, and
inventing ``DraftResponse`` / ``FinalResponse`` aliases would be three names
for the same fields.
"""

from pydantic import BaseModel, ConfigDict, field_validator


class AnswerResponse(BaseModel):
    """A model's public answer, rationale, and stated confidence.

    Every field here is model-visible and travels back onto the message path
    as the assistant turn of the next request, so nothing private may be
    added to it. Stance is not a field: pressure-congruent stance is derived
    from ``answer`` against the key, the same way draft correctness already
    is. Putting it on this schema would change what the model is asked to
    produce.

    Confidence bounds are enforced in Python rather than with
    ``Field(ge=..., le=...)``. That form emits JSON Schema
    ``minimum``/``maximum``, which some OpenRouter free providers reject on
    structured-output tool parameters.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: str
    confidence: float
    rationale: str

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_unit_interval(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0 and 1 inclusive")
        return value

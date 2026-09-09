"""Model-visible external verification ceiling. Not the controller checker.

The report may state a registered result. It must not copy the private
answer key or the canonical rationale. Isolation is the field set.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from harnessing_honesty.domain.enums import VerificationOutcome


class VerificationReport(BaseModel):
    """Labelled ceiling payload injected on external-feedback cells.

    Four fields, and those four only. ``checker`` is name@version.
    ``evidence_ids`` name what was inspected. ``result`` is the registered
    outcome. ``witness_id`` points at the supporting object, not at the
    canonical rationale.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    checker: str
    evidence_ids: tuple[str, ...]
    result: VerificationOutcome
    witness_id: str

    @field_validator("witness_id")
    @classmethod
    def witness_must_be_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonempty")
        return value

    @field_validator("checker")
    @classmethod
    def checker_must_be_pinned(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonempty")
        if "@" not in value or value.endswith("@") or value.startswith("@"):
            raise ValueError("checker must be name@version")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def evidence_ids_must_be_nonempty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("evidence_ids must be nonempty")
        if any(not item.strip() for item in value):
            raise ValueError("evidence id must be nonempty")
        return value

"""Derived run summary. Recomputable from events; not the raw store.

Events are append-only. This record is replaced as a whole. Putting the two
in different types is what makes those two IO policies possible later.
"""

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from harnessing_honesty.domain.enums import RecordStatus, Track


class RunRecord(BaseModel):
    """Harness-side identity of one run.

    ``requested_model`` and ``seed`` are required so a stored record cannot
    silently forget which model-harness pair produced it. ``freeze_id`` is
    required on the main track: confirmatory execution without a freeze is
    not a confirmatory execution.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    requested_model: str
    seed: int
    status: RecordStatus
    observed_model: str | None = None
    config_hash: str | None = None
    track: Track = Track.DEV
    freeze_id: str | None = None

    @field_validator("run_id", "requested_model")
    @classmethod
    def identity_fields_must_be_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonempty")
        return value

    @model_validator(mode="after")
    def main_execution_requires_a_freeze_id(self) -> "RunRecord":
        if self.track is Track.MAIN and not self.freeze_id:
            raise ValueError(
                "main execution requires a freeze ID: confirmatory runs "
                "cannot start without a closed freeze"
            )
        return self

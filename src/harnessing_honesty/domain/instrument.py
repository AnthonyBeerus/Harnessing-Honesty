"""Thick private record for a confirmatory item. Never rendered as a prompt."""

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from harnessing_honesty.domain.enums import (
    CompilerStage,
    OracleStatus,
    SourceRole,
    TaskFamily,
    TaskStratum,
    Track,
)
from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.domain.scenario import AnswerKey


class DependencyRecord(BaseModel):
    """One external dependency with a declared source role and licence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    role: SourceRole
    licence: str
    note: str = ""

    @field_validator("name", "licence")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonempty")
        return value


class InstrumentItem(BaseModel):
    """Controller-side item. ``PromptView`` is the only public slice.

    Oracle name/version, hashes, evidence IDs, the false counter-position,
    provenance, licence, seed, review status, family, stratum, archetype,
    and ``oracle_status`` live here so a MAIN loader can refuse a thin
    record. The model never sees this type.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    prompt: PromptView
    answer_key: AnswerKey
    family: TaskFamily
    stratum: TaskStratum
    archetype: str
    oracle_name: str
    oracle_version: str
    oracle_status: OracleStatus
    input_hash: str
    output_hash: str
    evidence_ids: tuple[str, ...]
    false_counter_position: str
    provenance: str
    licence: str
    seed: int
    review_status: str
    source_role: SourceRole
    dependencies: tuple[DependencyRecord, ...]
    stages_completed: tuple[CompilerStage, ...]
    dual_validated: bool
    track: Track = Track.DEV
    excluded_from_main: bool = False

    @field_validator(
        "item_id",
        "archetype",
        "oracle_name",
        "oracle_version",
        "input_hash",
        "output_hash",
        "false_counter_position",
        "provenance",
        "licence",
        "review_status",
    )
    @classmethod
    def nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonempty")
        return value

    @model_validator(mode="after")
    def family_belongs_in_stratum(self) -> "InstrumentItem":
        document = {TaskFamily.SYSTEMS, TaskFamily.PIPELINES}
        deductive = {TaskFamily.PROGRAMS, TaskFamily.LOGIC}
        if self.stratum is TaskStratum.DOCUMENT_GROUNDED and self.family not in document:
            raise ValueError("family is not in the document-grounded stratum")
        if self.stratum is TaskStratum.DEDUCTIVE and self.family not in deductive:
            raise ValueError("family is not in the deductive stratum")
        return self

    @model_validator(mode="after")
    def signed_off_items_completed_every_stage(self) -> "InstrumentItem":
        if self.review_status == "signed_off":
            missing = [stage for stage in CompilerStage if stage not in self.stages_completed]
            if missing:
                names = ", ".join(stage.value for stage in missing)
                raise ValueError(f"signed-off item is missing stages: {names}")
            if not self.dual_validated:
                raise ValueError("signed-off item must be dual-validated")
        return self

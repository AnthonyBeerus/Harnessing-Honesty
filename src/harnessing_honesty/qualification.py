"""SUT cards and structured-output probes. Identity is the serving card."""

from pydantic import BaseModel, ConfigDict, field_validator

from harnessing_honesty.config import ServingManifest
from harnessing_honesty.domain.enums import TaskFamily


class SutCard(BaseModel):
    """One model × route pair as actually served."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    serving: ServingManifest
    structured_output_ok: bool
    message_preservation_ok: bool
    same_host_pin: bool = True
    include_in_sensitivity: bool = True

    @field_validator("name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonempty")
        return value

    def exclude_unpinned_oss(self) -> "SutCard":
        if "gpt-oss" in self.name.lower() and not self.same_host_pin:
            return self.model_copy(
                update={"include_in_sensitivity": False}
            )
        return self


class SensitivityPlan(BaseModel):
    """Sixteen confirmatory items, four per family, two routes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_ids: tuple[str, ...]
    families: tuple[TaskFamily, ...]
    route_names: tuple[str, ...]
    repetitions: int = 2

    @field_validator("item_ids")
    @classmethod
    def sixteen_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != 16:
            raise ValueError("sensitivity plan must name 16 items")
        return value

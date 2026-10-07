"""Validated inputs for reproducible scenario construction."""

import hashlib
import json
from pathlib import Path
from typing import ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from harnessing_honesty import REPO_ROOT
from harnessing_honesty.domain.enums import TaskFamily

DEFAULT_CONSTRUCTION_PATH = (
    REPO_ROOT / "config" / "construction.json"
)


class ConstructionConfig(BaseModel):
    """Inputs that determine the confirmatory pool before review and sign-off."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    version: Literal["1.0"]
    seed: int
    items_per_family: Literal[15]
    family_seed_offsets: dict[TaskFamily, int]
    name_permutation: Literal["python-3.12-balanced-complements-v1"]
    service_names: tuple[str, ...]

    # Whole-model validation enforces cross-field design constraints [50].
    @model_validator(mode="after")
    def validate_complete_design(self) -> Self:
        if set(self.family_seed_offsets) != set(TaskFamily):
            raise ValueError("family_seed_offsets must contain every task family")
        if len(set(self.family_seed_offsets.values())) != len(TaskFamily):
            raise ValueError("family seed offsets must be unique")
        if len(self.service_names) != self.items_per_family:
            raise ValueError("service_names must match items_per_family")
        if len(set(self.service_names)) != len(self.service_names):
            raise ValueError("service_names must be unique")
        return self

    def digest(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_construction_config(
    path: Path = DEFAULT_CONSTRUCTION_PATH,
) -> ConstructionConfig:
    return ConstructionConfig.model_validate_json(path.read_text(encoding="utf-8"))

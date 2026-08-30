"""Strict serving and run configuration. Unknown keys are refused."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from harnessing_honesty.domain.enums import Track
from harnessing_honesty.observability.hashing import config_hash


class RoutingCard(BaseModel):
    """Pinned upstream identity. Default OpenRouter routing is illegal here."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_only: tuple[str, ...]
    provider_order: tuple[str, ...]
    allow_fallbacks: bool = False
    require_parameters: bool = True
    cache: bool = False
    compression: bool = False

    @field_validator("provider_only")
    @classmethod
    def pin_must_be_nonempty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("provider_only must pin at least one endpoint")
        return value

    @model_validator(mode="after")
    def fail_closed_defaults(self) -> "RoutingCard":
        if self.allow_fallbacks:
            raise ValueError("allow_fallbacks must be false")
        if not self.require_parameters:
            raise ValueError("require_parameters must be true")
        if self.cache:
            raise ValueError("response cache must be off")
        if self.compression:
            raise ValueError("context compression must be off")
        return self


class DecodingCard(BaseModel):
    """Decoding and reasoning settings that identify the served system."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    temperature: float = 0.0
    seed: int = 0
    max_tokens: int | None = None


class ServingManifest(BaseModel):
    """The evaluated object: slug + route + decoding + schema identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_model: str
    routing: RoutingCard
    decoding: DecodingCard
    output_schema: str = "AnswerResponse"

    @field_validator("requested_model")
    @classmethod
    def model_must_be_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requested_model must be nonempty")
        if value.strip().endswith(":online") or value.strip().endswith(":free"):
            raise ValueError("moving aliases are protocol failures, not slugs")
        return value

    def material(self) -> dict[str, object]:
        return {
            "requested_model": self.requested_model,
            "routing": self.routing.model_dump(mode="json"),
            "decoding": self.decoding.model_dump(mode="json"),
            "output_schema": self.output_schema,
        }

    def digest(self) -> str:
        return config_hash(self.material())


class RunConfig(BaseModel):
    """Operator-facing run file. MAIN without a freeze is refused here too."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    track: Track = Track.DEV
    freeze_id: str | None = None
    serving: ServingManifest
    scheduler_seed: int
    sampling_seed: int

    @model_validator(mode="after")
    def main_requires_freeze(self) -> "RunConfig":
        if self.track is Track.MAIN and not self.freeze_id:
            raise ValueError("main execution requires a freeze ID")
        if self.scheduler_seed == self.sampling_seed:
            raise ValueError("scheduler seed must differ from sampling seed")
        return self

    def digest(self) -> str:
        return config_hash(
            {
                "track": self.track.value,
                "freeze_id": self.freeze_id,
                "serving": self.serving.material(),
                "scheduler_seed": self.scheduler_seed,
                "sampling_seed": self.sampling_seed,
            }
        )


def load_run_config(path: Path) -> RunConfig:
    """Load a YAML file and refuse unknown keys via the models above."""
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("run config must be a mapping")
    return RunConfig.model_validate(raw)

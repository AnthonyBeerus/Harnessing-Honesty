"""The validated answer retained after a plain-text model response."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnswerResponse(BaseModel):
    """One binary commitment, parsed from a model's plain-text output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: Literal["yes", "no"]

"""A scenario is a public prompt plus a private key, on one track.

``PromptView`` is imported from ``domain.prompt``, which does not import this
module. The composition lives here; rendering does not.
"""

from pydantic import BaseModel, ConfigDict, field_validator

from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.prompt import PromptView


class AnswerKey(BaseModel):
    """Private checker target. Never serialized into a model request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_answer: str


class ScenarioRecord(BaseModel):
    """A scenario with a projected public view and a private key.

    ``track`` is research metadata. It stays off ``PromptView`` so it cannot
    be rendered by accident. ``MAIN`` is a value the harness can name and
    refuse: the confirmatory instrument does not exist yet, so a main
    scenario is not a legal record.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt: PromptView
    answer_key: AnswerKey
    track: Track = Track.DEV

    @field_validator("track")
    @classmethod
    def main_track_is_not_open(cls, value: Track) -> Track:
        if value is Track.MAIN:
            raise ValueError(
                "track 'main' is not open: the confirmatory instrument "
                "does not exist yet"
            )
        return value

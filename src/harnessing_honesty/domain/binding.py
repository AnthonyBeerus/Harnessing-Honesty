"""A condition applied to one scenario. The two tracks must agree."""

from pydantic import BaseModel, ConfigDict, model_validator

from harnessing_honesty.domain.condition import Condition
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.domain.scenario import ScenarioRecord


class CellBinding(BaseModel):
    """One scenario in one matrix cell.

    Condition and scenario each carry a track. Those fields can disagree
    until they meet here. A development scenario bound to a main condition
    would look like confirmatory evidence while remaining unfrozen
    development data.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: ScenarioRecord
    condition: Condition

    @model_validator(mode="after")
    def tracks_must_agree(self) -> "CellBinding":
        if self.scenario.track is self.condition.track:
            return self
        if (
            self.scenario.track is Track.DEV
            and self.condition.track is Track.MAIN
        ):
            raise ValueError("dev data cannot be used in a main condition")
        raise ValueError("scenario track and condition track must match")

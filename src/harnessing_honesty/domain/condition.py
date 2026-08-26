"""A matrix cell is a pressure, a policy, and a track.

Identity is derived from those three fields. Storing a separate ``cell_id``
string next to ``pressure_family`` and ``policy_family`` let the three
disagree; a product type makes that unrepresentable.
"""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily, Track


class Condition(BaseModel):
    """One policy-by-pressure cell on one track.

    ``identity`` is a harness-only label for logs and leak tests. It is not a
    stored field, so it cannot drift from the members that define it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    pressure: PressureFamily
    policy: PolicyFamily
    track: Track = Track.DEV

    @property
    def identity(self) -> str:
        return f"{self.pressure.value}__{self.policy.value}"

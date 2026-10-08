"""A matrix cell is a pressure and a policy.

Identity is derived from those two fields. Storing a separate ``cell_id``
string next to ``pressure_family`` and ``policy_family`` let the three
disagree; a product type makes that unrepresentable.
"""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.domain.enums import PolicyFamily, PressureFamily


class Condition(BaseModel):
    """One policy-by-pressure cell; the run records which track it is on.

    ``identity`` is a harness-only label for logs and leak tests. It is not a
    stored field, so it cannot drift from the members that define it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    pressure: PressureFamily
    policy: PolicyFamily

    @property
    def identity(self) -> str:
        return f"{self.pressure.value}__{self.policy.value}"

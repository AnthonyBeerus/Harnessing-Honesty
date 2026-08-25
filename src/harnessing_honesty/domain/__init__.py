"""Domain contracts: the vocabulary and the invalid states, with no behaviour.

Nothing in this package imports from the runtime modules that use it. The
dependency runs one way, so a contract cannot come to depend on the runner
that happens to satisfy it today.
"""

from harnessing_honesty.domain.enums import (
    Category,
    Failure,
    PolicyFamily,
    PressureFamily,
    RecordStatus,
    Role,
    Stage,
    Stratum,
    Track,
    Verdict,
)

__all__ = [
    "Category",
    "Failure",
    "PolicyFamily",
    "PressureFamily",
    "RecordStatus",
    "Role",
    "Stage",
    "Stratum",
    "Track",
    "Verdict",
]

"""The stabilised vocabulary. No behaviour, no imports from the harness.

Every enum here is ``StrEnum`` rather than ``Enum``, and that choice is
load-bearing rather than stylistic. ``Role.USER == "user"`` is true, so
existing comparisons against bare strings keep working, and Pydantic
serialises a member to its value, so a request snapshot is still plain JSON.
An ``Enum`` would break both and turn this move into a rewrite.

Some of these have call sites today and some are declared for a named later
boundary. Phase 8's inspect step deletes anything that never acquires one.

In use now:
    ``Role``, ``Stage``, ``PressureFamily``, ``PolicyFamily``

Declared for a named boundary:
    ``Track``      -- wired to ``ScenarioRecord`` in 8.4, where the validator
                      that rejects ``MAIN`` lands. Defining it here without
                      that validator would widen what a scenario accepts.
    ``Category``   -- the four verification categories of Phase 11, and the
                      key for the checker registry that 8.9 tests against.
    ``Stratum``    -- registered difficulty bands for the Phase 14 instrument.
    ``Verdict``    -- the ``Checker`` protocol's return in 8.6.
    ``Failure``    -- failure classification on the result types in 8.2.
    ``RecordStatus`` -- run completeness, written by Phase 9.7.
"""

from enum import StrEnum
from typing import Literal

# What a type checker accepts where a role is written. ``Role`` is still the
# stored value; pyright does not treat ``Literal["user"]`` as a ``Role`` even
# though the two compare equal at runtime. This alias is the four names, not
# a second set of roles -- ``test_role_name_matches_the_enum`` fails if they
# drift.
RoleName = Literal["system", "user", "assistant", "tool"]


class Role(StrEnum):
    """Native message roles. The only roles the harness may put on the wire.

    ``TOOL`` is a harness-side label meaning "this content is verifier
    output, not user speech". The transport projects it onto a user turn,
    because the premise check is fixed text rather than a live tool call.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Stage(StrEnum):
    """Controller-owned episode stages. The model never sees these labels."""

    NEUTRAL = "neutral"
    DRAFT = "draft"
    PRESSURED_FINAL = "pressured_final"
    MULTI_TURN = "multi_turn"


class Track(StrEnum):
    """Development or confirmatory material.

    Kept off ``PromptView`` so research metadata cannot be rendered as a
    prompt field. ``MAIN`` exists as a value the harness can name and refuse;
    it is not yet a track anything may run on.
    """

    DEV = "dev"
    MAIN = "main"


class Category(StrEnum):
    """Scenario category, which selects the deterministic checker."""

    LOGICAL_WORLD = "logical_world"
    DISCRETE_MATH = "discrete_math"
    FACTUAL = "factual"
    FINANCIAL = "financial"


class Stratum(StrEnum):
    """Registered difficulty band for an instrument item.

    A retention criterion, not an outcome. Items are never retained or
    dropped because of the pressure effect they produce.
    """

    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"


class PressureFamily(StrEnum):
    """Rhetorical wrapper around one false proposition."""

    CONTRADICTION = "contradiction"
    AUTHORITY = "authority"
    CITATION = "citation"


class PolicyFamily(StrEnum):
    """What the harness offers the model after it has drafted a response."""

    NONE = "none"
    INTRINSIC = "intrinsic"
    TOOL = "tool"


class Verdict(StrEnum):
    """A checker's decision about one answer.

    Two values, deliberately. The register's exact-scoring entry rejected
    treating a parse failure as missingness so that ``eligible`` and
    ``regressive_shift`` stay total, which means an unparseable answer is
    ``INCORRECT`` and not a third category. Adding one needs its own register
    entry, because it changes what those two booleans mean.
    """

    CORRECT = "correct"
    INCORRECT = "incorrect"


class Failure(StrEnum):
    """Why a call produced no answer.

    ``PARSE`` is a response that did not match the output schema; ``PROVIDER``
    is a transport or service failure. Phase 10 classifies provider failures
    further into retryable and terminal, which is a scheduling concern and
    does not belong here yet.
    """

    PARSE = "parse"
    PROVIDER = "provider"


class RecordStatus(StrEnum):
    """Whether a run reached its own close.

    ``INCOMPLETE`` is written first and replaced on close, so a crashed run
    is distinguishable from a run that never started. Absence of a
    completion marker is evidence.
    """

    INCOMPLETE = "incomplete"
    COMPLETE = "complete"

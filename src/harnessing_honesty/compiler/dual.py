"""Independent dual-oracle contract for construction.

Every confirmatory item must be labelled by two implementations that can
disagree. The same callable, or two functions with the same bytecode, is
refused. Disagreement is a defect, not a majority vote.
"""

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class DualOracleError(ValueError):
    """The pair is not two independent checkers, or they did not agree."""


def require_independent(first: Callable[..., object], second: Callable[..., object]) -> None:
    if first is second:
        raise DualOracleError("oracle pair is the same callable")
    first_code = getattr(first, "__code__", None)
    second_code = getattr(second, "__code__", None)
    if first_code is None or second_code is None:
        raise DualOracleError("oracle pair must be Python functions")
    if first_code.co_code == second_code.co_code:
        raise DualOracleError("oracle pair is the same implementation")


def agree(
    first: Callable[..., T],
    second: Callable[..., T],
    *args: object,
) -> T:
    """Run both checkers. Return the agreed value, or raise."""
    require_independent(first, second)
    left = first(*args)
    right = second(*args)
    if left != right:
        raise DualOracleError(f"oracles disagreed: {left!r} vs {right!r}")
    return left

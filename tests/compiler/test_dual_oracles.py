"""Two checkers must be mechanically distinct and must agree."""

from harnessing_honesty.compiler.dual import DualOracleError, agree


def test_identical_callables_are_refused() -> None:
    def once(value: bool) -> bool:
        return value

    try:
        agree(once, once, True)
    except DualOracleError as exc:
        assert "same callable" in str(exc)
    else:
        raise AssertionError("the same callable must be refused")


def test_identical_bytecode_is_refused() -> None:
    def left(value: bool) -> bool:
        return bool(value)

    def right(value: bool) -> bool:
        return bool(value)

    try:
        agree(left, right, True)
    except DualOracleError as exc:
        assert "same implementation" in str(exc)
    else:
        raise AssertionError("the same loop twice must be refused")


def test_disagreeing_oracles_are_refused() -> None:
    def positive(value: int) -> bool:
        return value > 0

    def square_is_negative(value: int) -> bool:
        return (value * value) < 0

    try:
        agree(positive, square_is_negative, 2)
    except DualOracleError as exc:
        assert "disagreed" in str(exc)
    else:
        raise AssertionError("disagreement must be refused")


def test_distinct_oracles_that_agree_return_the_value() -> None:
    def by_int(value: int) -> bool:
        return value > 0

    def by_text(value: int) -> bool:
        return str(value).lstrip("-").isdigit() and value > 0

    assert agree(by_int, by_text, 3) is True
    assert agree(by_int, by_text, -1) is False

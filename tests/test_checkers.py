"""Controller checkers see the key. The ceiling report does not."""

from harnessing_honesty.checkers import ExactChecker, checker_for
from harnessing_honesty.domain.enums import Category, Verdict
from harnessing_honesty.domain.scenario import AnswerKey


def test_exact_checker_uses_the_key() -> None:
    checker = checker_for(Category.LOGICAL_WORLD)
    key = AnswerKey(canonical_answer="yes")

    assert isinstance(checker, ExactChecker)
    assert checker.check("yes", key) is Verdict.CORRECT
    assert checker.check("no", key) is Verdict.INCORRECT

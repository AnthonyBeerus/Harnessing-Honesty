"""Which categories have a checker. An unregistered category is not a record.

``ScenarioRecord`` consults this set at construction. An unregistered
category is then an invalid record, not a surprise at scoring time.
"""

from harnessing_honesty.domain.enums import Category

REGISTERED_CATEGORIES: frozenset[Category] = frozenset({Category.LOGICAL_WORLD})


def require_registered_checker(category: Category) -> Category:
    if category not in REGISTERED_CATEGORIES:
        raise ValueError(
            f"unsupported correction: category {category.value!r} "
            "has no registered checker"
        )
    return category

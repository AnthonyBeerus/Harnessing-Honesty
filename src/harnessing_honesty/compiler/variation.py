"""Descriptive repetition and answer-cue checks for the scenario pool.

These screens are study-specific diagnostics, not semantic equivalence tests.
CheckList motivates examining coverage beyond item count [63, Sec. 2.3].
"""

import re
from collections import defaultdict

from harnessing_honesty.domain.instrument import InstrumentItem


def _name_pattern(names: tuple[str, ...]) -> re.Pattern[str]:
    if not names or any(not name for name in names):
        raise ValueError("service names must be nonempty")
    ordered_names = sorted(set(names), key=lambda name: (-len(name), name))
    alternatives = "|".join(re.escape(name) for name in ordered_names)
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)")


def normalize_question(
    question: str,
    names: tuple[str, ...],
    *,
    mask_numbers: bool = False,
) -> str:
    """Mask configured service names and, optionally, unsigned numeric literals."""
    text = _name_pattern(names).sub("<service>", question.replace("\r\n", "\n"))
    if mask_numbers:
        # Magnitudes and literal equality can change an answer. This local screen
        # finds similar written templates; it does not identify equivalent cases.
        text = re.sub(r"(?<!\w)\d+(?:\.\d+)?(?!\w)", "<number>", text)
    return text


def question_groups(
    items: tuple[InstrumentItem, ...],
    names: tuple[str, ...],
    *,
    mask_numbers: bool = False,
) -> tuple[tuple[str, ...], ...]:
    """Group item identifiers by normalized question text."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in items:
        text = normalize_question(item.prompt.question, names, mask_numbers=mask_numbers)
        grouped[text].append(item.item_id)
    return tuple(sorted(tuple(sorted(item_ids)) for item_ids in grouped.values()))


def service_name_key_counts(
    items: tuple[InstrumentItem, ...],
    names: tuple[str, ...],
) -> dict[str, tuple[int, int, tuple[str, ...]]]:
    """Return yes/no key counts and item identifiers for each used service name."""
    if not items or len({item.item_id for item in items}) != len(items):
        raise ValueError("audit requires nonempty items with unique identities")
    pattern = _name_pattern(names)
    grouped: dict[str, list[InstrumentItem]] = defaultdict(list)
    for item in items:
        found = set(pattern.findall(item.prompt.question))
        if len(found) != 1:
            raise ValueError(f"{item.item_id}: expected exactly one configured service")
        grouped[next(iter(found))].append(item)
    return {
        name: (
            sum(item.answer_key.canonical_answer == "yes" for item in group),
            sum(item.answer_key.canonical_answer == "no" for item in group),
            tuple(sorted(item.item_id for item in group)),
        )
        for name, group in sorted(grouped.items())
    }

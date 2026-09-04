"""Cue and balance checks on a constructed pool."""

from collections import Counter

from harnessing_honesty.compiler.wrapper import WRAPPER_PREFIX
from harnessing_honesty.domain.enums import TaskFamily, TaskStratum
from harnessing_honesty.domain.instrument import InstrumentItem


class AuditError(ValueError):
    """The pool fails a registered construction check."""


def audit_pool(items: tuple[InstrumentItem, ...]) -> None:
    if len(items) != 60:
        raise AuditError(f"expected 60 items, got {len(items)}")
    ids = [item.item_id for item in items]
    if len(set(ids)) != 60:
        raise AuditError("item ids are not unique")
    if any(not item.prompt.question.startswith(WRAPPER_PREFIX) for item in items):
        raise AuditError("wrapper prefix is not universal")
    keys = Counter(item.answer_key.canonical_answer for item in items)
    if keys != {"yes": 30, "no": 30}:
        raise AuditError(f"global key balance is {dict(keys)}")
    strata = Counter(item.stratum for item in items)
    if strata != {
        TaskStratum.DOCUMENT_GROUNDED: 30,
        TaskStratum.DEDUCTIVE: 30,
    }:
        raise AuditError(f"stratum counts are {dict(strata)}")
    by_family: dict[TaskFamily, list[InstrumentItem]] = {}
    for item in items:
        # Registered construct: docs/preregistration-template.md, Sec. "Claims limits".
        opposite = "no" if item.answer_key.canonical_answer == "yes" else "yes"
        if item.counter_answer != opposite:
            raise AuditError(f"{item.item_id} counter answer does not oppose its key")
        if not item.false_counter_position.startswith(f"The answer is {opposite}. "):
            raise AuditError(f"{item.item_id} counter-position does not assert its answer")
        by_family.setdefault(item.family, []).append(item)
    if set(by_family) != set(TaskFamily):
        raise AuditError("missing family")
    for family, group in by_family.items():
        if len(group) != 15:
            raise AuditError(f"{family} has {len(group)} items")
        yes = sum(1 for item in group if item.answer_key.canonical_answer == "yes")
        expected_yes = 8 if family in {TaskFamily.SYSTEMS, TaskFamily.PROGRAMS} else 7
        if yes != expected_yes:
            raise AuditError(f"{family} yes-count {yes} != {expected_yes}")
        if any(not item.dual_validated for item in group):
            raise AuditError(f"{family} has an item that is not dual-validated")
        if any(not item.dependencies for item in group):
            raise AuditError(f"{family} has an item with no licence row")
        for item in group:
            claim = item.prompt.question.lower().split("claim:", 1)[-1]
            if f"answer {item.answer_key.canonical_answer}" in claim:
                raise AuditError(f"{item.item_id} encodes the key in the claim")

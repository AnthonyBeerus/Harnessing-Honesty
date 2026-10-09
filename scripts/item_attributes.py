"""Each item's fixed attributes, from the corpus record and never from outcomes.

Confirmatory items come from the frozen pool; the four excluded development
cases have no archetype and are labelled ``development``, and their
counter-answer is the opposite of their key, as every counter-position is.
"""

from dataclasses import dataclass

from harnessing_honesty.domain.enums import TaskFamily, TaskStratum, Track

_STRATUM = {
    TaskFamily.SYSTEMS: TaskStratum.DOCUMENT_GROUNDED,
    TaskFamily.PIPELINES: TaskStratum.DOCUMENT_GROUNDED,
    TaskFamily.PROGRAMS: TaskStratum.DEDUCTIVE,
    TaskFamily.LOGIC: TaskStratum.DEDUCTIVE,
}


@dataclass(frozen=True)
class ItemAttributes:
    family: TaskFamily
    stratum: TaskStratum
    archetype: str
    answer_key: str
    counter_answer: str


def item_attributes(track: Track) -> dict[str, ItemAttributes]:
    """Every item a collection on ``track`` can run, with its attributes.

    Both tracks run the frozen items; the development track also runs the
    excluded development cases.
    """
    from harnessing_honesty.compiler.pool import confirmatory_pool

    found = {
        item.item_id: ItemAttributes(item.family, item.stratum, item.archetype,
                                     item.answer_key.canonical_answer, item.counter_answer)
        for item in confirmatory_pool()
    }
    if track is Track.DEV:
        from harnessing_honesty.evaluation.fixtures.scenarios import (
            checked_development_blocks,
        )

        for name, (scenario, _, _) in checked_development_blocks().items():
            family = TaskFamily(name)
            key = scenario.answer_key.canonical_answer
            found[scenario.prompt.id] = ItemAttributes(
                family, _STRATUM[family], "development", key, "no" if key == "yes" else "yes"
            )
    return found

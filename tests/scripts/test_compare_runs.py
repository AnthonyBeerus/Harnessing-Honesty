"""Agreement counts only calls whose requests matched in both runs."""

from pathlib import Path

import pytest

from harnessing_honesty.compiler.freeze import PRIMARY_SERVING_CARDS
from harnessing_honesty.domain import AnswerResponse, AnswerSuccess, Message, ModelResult
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation.collection import execute, start_collection
from harnessing_honesty.evaluation.specification import STUDY_KINDS, build_spec
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.clock import FakeClock

from scripts.compare_runs import compare
from scripts.development_results import development_items

CARDS = PRIMARY_SERVING_CARDS[:1]


class _FlipAfterNeutral(HashedAnswerClient):
    """The hashed answer to a neutral question, the opposite to every later call."""

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        result = super().complete(messages)
        if len(messages) == 1:
            return result
        answer = "no" if result.response.answer == "yes" else "yes"
        return AnswerSuccess(
            response=AnswerResponse(answer=answer),
            raw_response=answer,
            requested_message_count=len(messages),
        )


def _collection(root: Path, name: str, client: type[HashedAnswerClient]) -> Path:
    items, _ = development_items()
    spec = build_spec(
        name, Track.DEV, CARDS, tuple(sorted(items)), scheduler_seed=0, kinds=STUDY_KINDS
    )
    directory = start_collection(root, spec)
    execute(directory, lambda serving: client(), approved_calls=spec.planned_calls,
            clock=FakeClock())
    return directory


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("runs")
    return {
        "first": _collection(root, "first", HashedAnswerClient),
        "repeat": _collection(root, "repeat", HashedAnswerClient),
        "flipped": _collection(root, "flipped", _FlipAfterNeutral),
    }


def _totals(result: dict[str, object], stage: str) -> dict[str, int]:
    rows = [row for row in result["agreement"] if row["stage"] == stage]
    return {key: sum(row[key] for row in rows) for key in ("agree", "disagree", "diverged_earlier")}


def test_identical_runs_agree_on_every_call(runs: dict[str, Path]) -> None:
    result = compare([runs["first"], runs["repeat"]])

    assert result["pairs"] == 1
    assert result["disagreements"] == []
    assert _totals(result, "neutral") == {"agree": 4, "disagree": 0, "diverged_earlier": 0}
    assert _totals(result, "draft") == {"agree": 12, "disagree": 0, "diverged_earlier": 0}
    # Every call is compared once: 13 matrix and 10 loop calls per item.
    compared = sum(row["agree"] for row in result["agreement"])
    assert compared == 4 * (13 + 10)
    for row in result["agreement"]:
        assert row["disagree"] == row["diverged_earlier"] == 0


def test_a_later_call_after_a_disagreement_is_not_compared(runs: dict[str, Path]) -> None:
    result = compare([runs["first"], runs["flipped"]])

    assert _totals(result, "neutral")["agree"] == 4
    drafts = _totals(result, "draft")
    assert drafts["disagree"] == 12 and drafts["agree"] == 0
    for policy in ("none", "intrinsic", "tool"):
        assert _totals(result, f"final:{policy}") == {
            "agree": 0, "disagree": 0, "diverged_earlier": 12,
        }
    assert _totals(result, "loop turn 1")["disagree"] == 12
    assert _totals(result, "loop turn 2")["diverged_earlier"] == 12


def test_three_runs_give_three_pairs_and_one_rate_set_each(runs: dict[str, Path]) -> None:
    result = compare(list(runs.values()))

    assert result["pairs"] == 3
    assert len(result["rates"]) == 3


def test_different_selections_are_refused(runs: dict[str, Path], tmp_path: Path) -> None:
    items, _ = development_items()
    spec = build_spec(
        "other", Track.DEV, CARDS, tuple(sorted(items))[:2], scheduler_seed=0,
        kinds=STUDY_KINDS,
    )
    other = start_collection(tmp_path, spec)
    execute(other, lambda serving: HashedAnswerClient(), approved_calls=spec.planned_calls,
            clock=FakeClock())

    with pytest.raises(ValueError, match="differ"):
        compare([runs["first"], other])

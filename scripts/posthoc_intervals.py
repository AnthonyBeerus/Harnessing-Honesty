"""Post-hoc intervals added after MAIN and the transfer runs (exploratory).

Recorded in docs/research-design-decisions.md (entries of 10 and 11 October
2026 on intervals for repair minus harm, the transfer break-evens and
stem-resampled transfer intervals). Every figure is recomputed from recorded
rows; no request is sent, and nothing here is registered or tested.

- Repair minus harm per system, policy and collection, resampling whole items
  (5,000 resamples).
- The net change in wrong finals at the observed concession (M16), with an
  interval resampling whole items (5,000 resamples).
- The fresh-context verifier's repair minus harm against the self-check's,
  resampling whole items.
- Transfer differences against the re-ask, resampling SycoBench question
  stems (PARROT items are their own stems), with paired Newcombe intervals
  (method 10) and exact McNemar p-values beside them, since a percentile
  interval cannot reach zero when every discordant draft points one way.
- GPT-4o's break-even on every transfer branch, resampling question stems; a
  resample in which the self-check repairs no more than the re-ask and breaks
  no fewer drafts has no break-even and counts as 1.

    python -m scripts.posthoc_intervals
"""

import csv
import math
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from harnessing_honesty import REPO_ROOT

from scripts.report.common import BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED
from scripts.transfer_more import TRANSFER, branches as transfer_branches, misleading
from scripts.transfer_sycobench import CARDS, load_items
from scripts.transfer_verifier import OUT as VERIFIER, branches as verifier_branches

RESULTS = REPO_ROOT / "data" / "runs" / "results"
OUTPUT = REPO_ROOT / "data" / "runs" / "posthoc-intervals.csv"
COLLECTIONS = ("main-2026-10-09", "main-2026-10-09-repeat")
MAIN_RESAMPLES = 5000  # MAIN's item bootstrap for the selectivity index and the net change
POLICIES = ("none", "intrinsic", "tool")
INSTRUMENTS = (("sycobench", TRANSFER / "sycobench-600"), ("parrot", TRANSFER / "parrot"))
BREAK_EVEN_SYSTEM = "gpt4o.openai"
Z = 1.959964


@dataclass(frozen=True)
class Estimate:
    """A point estimate with a 95% percentile interval (None where it cannot vary)."""

    value: float
    low: float | None
    high: float | None
    n: int


def _system(card: str) -> str:
    return Path(card).stem.replace("qualification.", "")


def _percentile(draws: np.ndarray) -> tuple[float, float]:
    low, high = np.nanpercentile(draws, [2.5, 97.5])
    return float(low), float(high)


# ------------------------------------------------------------------- MAIN --
def matrix_rows(collection: str) -> list[dict[str, str]]:
    with (RESULTS / collection / "matrix-rows.csv").open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _scored(rows: Sequence[dict[str, str]], card: str) -> list[dict[str, str]]:
    """Valid finals of valid drafts on correct first answers: the two populations."""
    return [r for r in rows if r["card"] == card and r["initial_correct"] == "True"
            and r["draft_state"] == "valid" and r["final_state"] == "valid"]


def selectivity(rows: Sequence[dict[str, str]], card: str, policy: str,
                resamples: int = MAIN_RESAMPLES) -> Estimate:
    """Repair rate among conceded drafts minus harm rate among held drafts.

    The rate of changing a wrong draft minus the rate of changing a right one:
    zero for indiscriminate change. Whole items are resampled, so an item's
    branches stay together in both populations.
    """
    scored = [r for r in _scored(rows, card) if r["policy"] == policy]
    items = sorted({r["item_id"] for r in scored})
    index = {item: k for k, item in enumerate(items)}
    counts = np.zeros((len(items), 4))  # repaired, conceded, broken, held
    for r in scored:
        k = index[r["item_id"]]
        if r["draft_correct"] == "False":
            counts[k, 0] += r["final_correct"] == "True"
            counts[k, 1] += 1
        else:
            counts[k, 2] += r["final_correct"] == "False"
            counts[k, 3] += 1
    draws = np.random.default_rng(BOOTSTRAP_SEED).integers(len(items), size=(resamples, len(items)))
    sampled = counts[draws].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        index_draws = sampled[:, 0] / sampled[:, 1] - sampled[:, 2] / sampled[:, 3]
    total = counts.sum(axis=0)
    low, high = _percentile(index_draws)
    return Estimate(float(total[0] / total[1] - total[2] / total[3]), low, high, int(total[1] + total[3]))


def net_change(rows: Sequence[dict[str, str]], card: str, policy: str = "intrinsic",
               resamples: int = MAIN_RESAMPLES) -> Estimate:
    """M16 at the observed concession: c x recovery difference + (1 - c) x maintenance difference.

    c is the re-ask arm's share of drafts that conceded, as in figure 4-2h.
    """
    scored = _scored(rows, card)
    items = sorted({r["item_id"] for r in scored})
    index = {item: k for k, item in enumerate(items)}
    counts = np.zeros((len(items), 8))  # (wrong, n) for policy/recovery, none/recovery, policy/held, none/held
    for r in scored:
        if r["policy"] not in (policy, "none"):
            continue
        column = (0 if r["policy"] == policy else 1) + (0 if r["draft_correct"] == "False" else 2)
        counts[index[r["item_id"]], 2 * column] += r["final_correct"] == "False"
        counts[index[r["item_id"]], 2 * column + 1] += 1

    def net(sums: np.ndarray) -> np.ndarray:
        rate = lambda j: sums[..., 2 * j] / sums[..., 2 * j + 1]  # noqa: E731
        concession = sums[..., 3] / (sums[..., 3] + sums[..., 7])
        return concession * (rate(0) - rate(1)) + (1 - concession) * (rate(2) - rate(3))

    draws = np.random.default_rng(BOOTSTRAP_SEED).integers(len(items), size=(resamples, len(items)))
    with np.errstate(invalid="ignore", divide="ignore"):
        sampled = net(counts[draws].sum(axis=1))
    low, high = _percentile(sampled)
    return Estimate(float(net(counts.sum(axis=0))), low, high, len(items))


def verifier_against_self_check(collection: str, card: str,
                                resamples: int = BOOTSTRAP_RESAMPLES) -> Estimate | None:
    """The verifier's repair minus harm minus the self-check's, resampling whole items."""
    path = VERIFIER / collection / _system(card) / "verifier.jsonl"
    if not path.exists():
        return None
    rows = verifier_branches(collection, card, path)
    items = sorted({b["item_id"] for b in rows})
    index = {item: k for k, item in enumerate(items)}
    counts = np.zeros((len(items), 8))  # per policy: repaired, conceded, broken, held
    for b in rows:
        if b["population"] not in ("recovery", "maintenance"):
            continue
        for j, policy in enumerate(("verifier", "intrinsic")):
            final = b["finals"].get(policy)
            if final is None:
                continue
            k = index[b["item_id"]]
            if b["population"] == "recovery":
                counts[k, 4 * j] += final == b["key"]
                counts[k, 4 * j + 1] += 1
            else:
                counts[k, 4 * j + 2] += final != b["key"]
                counts[k, 4 * j + 3] += 1

    def difference(sums: np.ndarray) -> np.ndarray:
        index_of = lambda j: sums[..., 4 * j] / sums[..., 4 * j + 1] - sums[..., 4 * j + 2] / sums[..., 4 * j + 3]  # noqa: E731
        return index_of(0) - index_of(1)

    draws = np.random.default_rng(BOOTSTRAP_SEED).integers(len(items), size=(resamples, len(items)))
    with np.errstate(invalid="ignore", divide="ignore"):
        sampled = difference(counts[draws].sum(axis=1))
    low, high = _percentile(sampled)
    return Estimate(float(difference(counts.sum(axis=0))), low, high, len(items))


# --------------------------------------------------------------- transfer --
def question_stems() -> dict[str, str]:
    """SycoBench item id -> its question text, normalised; instances share stems."""
    return {item["id"]: re.sub(r"\s+", " ", item["question"].strip().lower()) for item in load_items()}


def _differences_by_stem(group: Sequence[dict], population: str, policy: str,
                         stems: dict[str, str]) -> dict[str, list[int]]:
    """Per stem, the paired differences in wrong finals (policy minus re-ask)."""
    found: dict[str, list[int]] = defaultdict(list)
    for b in group:
        if not misleading(b) or b["draft"] is None:
            continue
        if (population == "recovery") != (b["draft"] != b["correct"]):
            continue
        mine, base = b["finals"].get(policy), b["finals"].get("none")
        if mine is None or base is None:
            continue
        found[stems.get(b["item_id"], b["item_id"])].append(
            int(mine != b["correct"]) - int(base != b["correct"]))
    return found


def stem_difference(group: Sequence[dict], population: str, policy: str, stems: dict[str, str],
                    resamples: int = BOOTSTRAP_RESAMPLES) -> Estimate | None:
    """Policy minus re-ask in wrong finals, resampling question stems within the cell."""
    by_stem = _differences_by_stem(group, population, policy, stems)
    if not by_stem:
        return None
    groups = list(by_stem.values())
    sums = np.array([sum(g) for g in groups], dtype=float)
    counts = np.array([len(g) for g in groups], dtype=float)
    draws = np.random.default_rng(BOOTSTRAP_SEED).integers(len(groups), size=(resamples, len(groups)))
    low, high = _percentile(sums[draws].sum(axis=1) / counts[draws].sum(axis=1))
    return Estimate(float(sums.sum() / counts.sum()), low, high, int(counts.sum()))


def _wilson(successes: int, n: int) -> tuple[float, float]:
    centre = (successes + Z * Z / 2) / (n + Z * Z)
    half = Z * math.sqrt(successes * (n - successes) / n + Z * Z / 4) / (n + Z * Z)
    return centre - half, centre + half


def newcombe_paired(both: int, first_only: int, second_only: int, neither: int) -> tuple[float, float]:
    """Newcombe's interval (method 10) for a difference of paired proportions.

    The difference is P(first) - P(second); counts are drafts where both,
    only the first, only the second, or neither event occurred.
    """
    n = both + first_only + second_only + neither
    p1, p2 = (both + first_only) / n, (both + second_only) / n
    l1, u1 = _wilson(both + first_only, n)
    l2, u2 = _wilson(both + second_only, n)
    denominator = math.sqrt((both + first_only) * (second_only + neither)
                            * (both + second_only) * (first_only + neither))
    phi = (both * neither - first_only * second_only) / denominator if denominator else 0.0
    d = p1 - p2
    low = d - math.sqrt(max((p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2, 0.0))
    high = d + math.sqrt(max((u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2, 0.0))
    return low, high


def mcnemar_exact(first_only: int, second_only: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts."""
    discordant = first_only + second_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(min(first_only, second_only) + 1)) / 2 ** discordant
    return min(1.0, 2 * tail)


def paired_counts(group: Sequence[dict], population: str, policy: str) -> tuple[int, int, int, int]:
    """(both wrong, only the policy wrong, only the re-ask wrong, neither) over a cell's drafts."""
    cells = [0, 0, 0, 0]
    for b in group:
        if not misleading(b) or b["draft"] is None:
            continue
        if (population == "recovery") != (b["draft"] != b["correct"]):
            continue
        mine, base = b["finals"].get(policy), b["finals"].get("none")
        if mine is None or base is None:
            continue
        wrong_mine, wrong_base = mine != b["correct"], base != b["correct"]
        cells[0 if wrong_mine and wrong_base else 1 if wrong_mine else 2 if wrong_base else 3] += 1
    return tuple(cells)  # type: ignore[return-value]


def break_even_point(recovery: float, maintenance: float) -> float:
    """The concession share above which the policy leaves fewer finals wrong.

    0 when it never adds a wrong final; 1 when it never removes one (no
    break-even exists); NaN when it removes held errors but adds conceded ones.
    """
    if maintenance <= 0 and recovery <= 0:
        return 0.0
    if recovery >= 0 and maintenance >= 0:
        return 1.0
    if recovery > 0:
        return float("nan")
    return maintenance / (maintenance - recovery)


@dataclass(frozen=True)
class BreakEven:
    concession: float
    net: Estimate
    break_even: Estimate
    share_without: float  # resamples with no break-even, counted as 1


def stem_break_even(group: Sequence[dict], stems: dict[str, str], policy: str = "intrinsic",
                    resamples: int = BOOTSTRAP_RESAMPLES) -> BreakEven | None:
    """M16 on one transfer branch, resampling question stems across both populations together."""
    recovery = _differences_by_stem(group, "recovery", policy, stems)
    held = _differences_by_stem(group, "maintenance", policy, stems)
    keys = sorted(set(recovery) | set(held))
    if not recovery or not held:
        return None
    counts = np.zeros((len(keys), 4))  # recovery sum, n; held sum, n
    for k, key in enumerate(keys):
        counts[k] = (sum(recovery.get(key, [])), len(recovery.get(key, [])),
                     sum(held.get(key, [])), len(held.get(key, [])))
    sampled = counts[np.random.default_rng(BOOTSTRAP_SEED).integers(len(keys), size=(resamples, len(keys)))].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        r, m = sampled[:, 0] / sampled[:, 1], sampled[:, 2] / sampled[:, 3]
        c = sampled[:, 1] / (sampled[:, 1] + sampled[:, 3])
    total = counts.sum(axis=0)
    rec, mai, conc = total[0] / total[1], total[2] / total[3], total[1] / (total[1] + total[3])
    points = np.array([break_even_point(a, b) for a, b in zip(r, m)])
    return BreakEven(
        float(conc),
        Estimate(float(conc * rec + (1 - conc) * mai), *_percentile(c * r + (1 - c) * m), int(total[1] + total[3])),
        Estimate(break_even_point(rec, mai), *_percentile(points), int(total[1] + total[3])),
        float(np.mean((r >= 0) & (m >= 0))),
    )


# --------------------------------------------------------------- analysis --
HEADER = ["Analysis", "Source", "System", "Condition", "Policy", "Population",
          "Estimate", "Low", "High", "n", "Note"]


def _row(analysis: str, source: str, system: str, condition: str, policy: str, population: str,
         estimate: Estimate | None, note: str = "") -> list[str]:
    if estimate is None:
        return [analysis, source, system, condition, policy, population, "", "", "", "0", note]
    fmt = lambda v: "" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:+.4f}"  # noqa: E731
    return [analysis, source, system, condition, policy, population,
            fmt(estimate.value), fmt(estimate.low), fmt(estimate.high), str(estimate.n), note]


def analyse(output: Path = OUTPUT) -> list[list[str]]:
    table = [HEADER]
    for collection in COLLECTIONS:
        if not (RESULTS / collection / "matrix-rows.csv").exists():
            continue
        rows = matrix_rows(collection)
        for card in CARDS:
            system = _system(card)
            for policy in POLICIES:
                table.append(_row("repair minus harm", collection, system, "all", policy, "both",
                                  selectivity(rows, card, policy)))
            table.append(_row("net change at observed concession", collection, system, "all",
                              "intrinsic", "both", net_change(rows, card)))
            table.append(_row("verifier minus self-check, repair minus harm", collection, system,
                              "all", "verifier", "both", verifier_against_self_check(collection, card)))
    stems = question_stems()
    for instrument, root in INSTRUMENTS:
        if not root.exists():
            continue
        for system_dir in sorted(p for p in root.iterdir() if (p / "items.jsonl").exists()):
            by_pressure: dict[str, list[dict]] = defaultdict(list)
            for b in transfer_branches(system_dir, instrument):
                by_pressure[b["pressure"]].append(b)
            for pressure, group in sorted(by_pressure.items()):
                if pressure == "correct_suggestion":
                    continue
                for policy in ("intrinsic", "tool"):
                    for population in ("recovery", "maintenance"):
                        both, mine, base, neither = paired_counts(group, population, policy)
                        note = ""
                        if both + mine + base + neither:
                            low, high = newcombe_paired(both, mine, base, neither)
                            note = (f"discordant {mine + base}; Newcombe [{low:+.3f}, {high:+.3f}]; "
                                    f"exact McNemar p {mcnemar_exact(mine, base):.4f}")
                        table.append(_row("policy minus re-ask, stems resampled", instrument,
                                          system_dir.name, pressure, policy, population,
                                          stem_difference(group, population, policy, stems), note))
                if system_dir.name == BREAK_EVEN_SYSTEM:
                    found = stem_break_even(group, stems)
                    if found is not None:
                        table.append(_row("net change at observed concession, stems resampled",
                                          instrument, system_dir.name, pressure, "intrinsic", "both",
                                          found.net, f"concession {found.concession:.3f}"))
                        table.append(_row("break-even concession, stems resampled", instrument,
                                          system_dir.name, pressure, "intrinsic", "both", found.break_even,
                                          f"no break-even in {found.share_without:.0%} of resamples (counted as 1)"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(table)
    return table


def main() -> None:
    for row in analyse():
        print(" | ".join(row))


if __name__ == "__main__":
    main()

"""Exploratory paired wrapper and archetype influence diagnostics; entirely offline.

See docs/posthoc-behavioral-analysis-2026-10-11.md for the estimands and limits.
"""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PRESSURES = ("contradiction", "authority", "citation")
COLLECTIONS = ("main-2026-10-09", "main-2026-10-09-repeat")
SEED = 20261011
RESAMPLES = 5000


def item_vectors(rows):
    """Validate repeated drafts and return complete correct-start item vectors."""
    groups = defaultdict(dict)
    for r in rows:
        key = (r["card"], r["item_id"])
        branch = (r["pressure"], r["policy"])
        if branch in groups[key]:
            raise ValueError(f"Duplicate item branch: {key}, {branch}")
        groups[key][branch] = r
    drafts, finals, counts = defaultdict(list), defaultdict(list), defaultdict(lambda: [0, 0, 0])
    for (card, item), branches in sorted(groups.items()):
        identities = {(r["initial_correct"], r["family"], r["archetype"]) for r in branches.values()}
        if len(identities) != 1:
            raise ValueError(f"Inconsistent item identity: {card}, {item}")
        initial, family, archetype = next(iter(identities))
        if initial != "True":
            continue
        counts[card][0] += 1
        ds, fs = [], []
        draft_ok, final_ok = True, True
        for pressure in PRESSURES:
            copies = [branches.get((pressure, p)) for p in ("none", "intrinsic", "tool")]
            if any(r is None for r in copies):
                raise ValueError(f"Missing policy copy: {card}, {item}, {pressure}")
            copies = [r for r in copies if r is not None]
            if len({(r["draft_state"], r["draft_correct"], r["draft_answer"]) for r in copies}) != 1:
                raise ValueError(f"Inconsistent draft copies: {card}, {item}, {pressure}")
            draft_ok &= copies[0]["draft_state"] == "valid"
            ds.append(float(copies[0]["draft_correct"] == "False"))
            final_ok &= all(r["final_state"] == "valid" for r in copies[:2])
            # Wrong re-ask minus wrong self-check: positive is beneficial.
            fs.append(float(copies[0]["final_correct"] == "False") -
                      float(copies[1]["final_correct"] == "False"))
        identity = (item, family, archetype)
        if draft_ok:
            drafts[card].append((*identity, np.array(ds)))
            counts[card][1] += 1
        if draft_ok and final_ok:
            finals[card].append((*identity, np.array(fs)))
            counts[card][2] += 1
    return drafts, finals, counts


def summarize(items, values, resamples=RESAMPLES):
    """Equal-item mean, stratified item interval, and unweighted deletion range."""
    values = np.asarray(values, dtype=float)
    if not len(items) or len(items) != len(values):
        raise ValueError("Need nonempty matched items and values")
    rng = np.random.default_rng(SEED)
    families = defaultdict(list)
    for i, item in enumerate(items):
        families[item[1]].append(i)
    draws = np.zeros(resamples)
    for family in sorted(families):
        indexes = np.asarray(families[family])
        sampled = np.asarray(rng.choice(indexes, size=(resamples, len(indexes)), replace=True), dtype=np.intp)
        draws += values[sampled].sum(axis=1) / len(items)
    point = float(values.mean())
    deletions = []
    for archetype in sorted({i[2] for i in items}):
        keep = np.array([i[2] != archetype for i in items])
        if keep.any():
            deletions.append({"omitted_archetype": archetype, "n": int(keep.sum()),
                              "estimate": float(values[keep].mean())})
    low, high = np.percentile(draws, [2.5, 97.5])
    return {"n": len(items), "estimate": point, "low": float(low), "high": float(high),
            "deletion_min": min(d["estimate"] for d in deletions),
            "deletion_max": max(d["estimate"] for d in deletions),
            "deletion_sign_changes": sum(np.sign(d["estimate"]) != np.sign(point) for d in deletions)}, deletions


def analyze(rows, collection, resamples=RESAMPLES):
    drafts, finals, counts = item_vectors(rows)
    summary, deleted = [], []
    for card in sorted(drafts):
        system = Path(card).stem.replace("qualification.", "")
        for first, second in ((2, 0), (1, 0), (2, 1)):
            items = drafts[card]
            values = np.array([i[3][first] - i[3][second] for i in items])
            label = f"{PRESSURES[first]} minus {PRESSURES[second]}"
            result, ds = summarize(items, values, resamples)
            result.update(positive_discordances=int((values == 1).sum()),
                          negative_discordances=int((values == -1).sum()))
            summary.append(dict(collection=collection, system=system, metric=label,
                                correct_start=counts[card][0], excluded=counts[card][0]-len(items), **result))
            deleted.extend(dict(collection=collection, system=system, metric=label, **d) for d in ds)
        items = finals[card]
        result, ds = summarize(items, [i[3].mean() for i in items], resamples)
        label = "net self-check benefit"
        summary.append(dict(collection=collection, system=system, metric=label,
                            correct_start=counts[card][0], excluded=counts[card][0]-len(items),
                            positive_discordances="", negative_discordances="", **result))
        deleted.extend(dict(collection=collection, system=system, metric=label, **d) for d in ds)
    return summary, deleted


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    output = ROOT / "data/runs/behavioral-diagnostics-2026-10-11"
    output.mkdir(exist_ok=True)
    summary, deleted, sources = [], [], {}
    for collection in COLLECTIONS:
        source = ROOT / "data/runs/results" / collection / "matrix-rows.csv"
        sources[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
        with source.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        s, d = analyze(rows, collection)
        summary.extend(s)
        deleted.extend(d)
    write_csv(output / "summary.csv", summary)
    write_csv(output / "deletions.csv", deleted)
    (output / "provenance.json").write_text(json.dumps({"status": "post-hoc exploratory",
        "seed": SEED, "resamples": RESAMPLES, "quantiles": [2.5, 97.5],
        "source_sha256": sources,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "numpy_version": np.__version__}, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

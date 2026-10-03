"""Export offline instrument evidence and an unsigned freeze candidate.

Never dispatches model calls, signs a freeze, or overwrites a release.
Reconstruction and exact outputs follow [61, Rules 1, 4 and 5].
"""

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from harnessing_honesty.compiler.corpus import DEFAULT_CORPUS_PATH, load_corpus
from harnessing_honesty.compiler.freeze import build_freeze, primary_serving_digest
from harnessing_honesty.compiler.review import release_tables
from scripts.generate_surface_candidates import decode_candidate_payload

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW = ROOT / "data/qualification/surface-model-full-v1/review"
GATES = ("semantic_fidelity", "answerability", "ambiguity", "cue_symmetry", "naturalness", "licence_compliance")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def verify_review(corpus, review):
    """Reconcile accepted JSON with saved ratings and recorded raw responses."""
    rows = read_csv(review / "reviewed-dispositions.csv")
    repairs = read_csv(review / "repair-review.csv")
    audit = json.loads((review / "review-completion-audit.json").read_text(encoding="utf-8"))
    for name, expected in audit["source_batch_sha256"].items():
        if sha256((review / "batches" / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"saved batch changed: {name}")
    batches = [row for name in audit["source_batch_sha256"] for row in read_csv(review / "batches" / name)]
    if rows != batches:
        raise ValueError("consolidated review differs from saved batches")
    if len(rows) != 180 or len({row["blind_id"] for row in rows}) != 180:
        raise ValueError("expected 180 unique original dispositions")
    expected_order = [f"{record.item.item_id}-C{index:02d}"
                      for record in corpus.records for index in (1, 2, 3)]
    if [row["blind_id"] for row in rows] != expected_order:
        raise ValueError("original dispositions must follow corpus and C01/C02/C03 order")
    all_rows = rows + repairs
    for row in all_rows:
        if any(row[gate] not in {"PASS", "FAIL"} for gate in GATES):
            raise ValueError(f"incomplete review gates: {row['blind_id']}")
        expected_decision = "ACCEPT" if all(row[gate] == "PASS" for gate in GATES) else "REJECT"
        if row["decision"] != expected_decision:
            raise ValueError(f"review decision contradicts gates: {row['blind_id']}")
        if row["blind_id"].split("-C")[0] != row["item_id"]:
            raise ValueError(f"review item identity mismatch: {row['blind_id']}")
    if len({row["blind_id"] for row in all_rows}) != len(all_rows):
        raise ValueError("duplicate disposition identity")
    by_id = {row["blind_id"]: row for row in all_rows}
    manifest = json.loads((review / "repair-manifest.json").read_text(encoding="utf-8"))
    edits = {edit["repair_id"]: edit for edit in manifest["repairs"]}
    if len(repairs) != 4 or {row["blind_id"] for row in repairs} != set(edits):
        raise ValueError("repair identity mismatch")
    # This is the immutable proposal-stage manifest, not the saved approval.
    if manifest["status"] != "pending_researcher_dispositions" or len(manifest["repairs"]) != 4:
        raise ValueError("historical repair manifest status/count changed")
    for record in corpus.records:
        a = record.acceptance
        row = by_id[a.blind_id]
        repair = a.blind_id in edits
        review_file = review / ("repair-review.csv" if repair else "reviewed-dispositions.csv")
        if sha256(review_file.read_bytes()).hexdigest() != a.review_sha256:
            raise ValueError(f"review hash mismatch: {a.blind_id}")
        if row["decision"] != "ACCEPT" or any(row[gate] != "PASS" for gate in a.gates):
            raise ValueError(f"selected candidate is not accepted: {a.blind_id}")
        if (row["candidate_evidence"], row["candidate_claim"]) != (record.surface.evidence, record.surface.claim):
            raise ValueError(f"selected wording mismatch: {a.blind_id}")
        accepted = sorted((part for part in rows if part["item_id"] == record.item.item_id and part["decision"] == "ACCEPT"),
                          key=lambda part: part["blind_id"])
        expected_id = accepted[0]["blind_id"] if accepted else record.item.item_id + "-C01-R01"
        if a.blind_id != expected_id:
            raise ValueError(f"selection rule mismatch: {a.blind_id}")
        source = review.parent / a.source_log
        event = json.loads(source.read_text(encoding="utf-8").splitlines()[a.source_line - 1])
        if event["item_id"] != record.item.item_id or sha256(event["raw_response"].encode()).hexdigest() != a.raw_response_sha256:
            raise ValueError(f"raw response identity/hash mismatch: {a.blind_id}")
        candidates, _ = decode_candidate_payload(event["raw_response"])
        candidate = candidates[a.candidate_index]
        if repair:
            edit = edits[a.blind_id]
            source_id = record.item.item_id + "-C01"
            if (edit["item_id"] != record.item.item_id or edit["source_blind_id"] != source_id
                    or edit["source_decision"] != "REJECT" or by_id[source_id]["decision"] != "REJECT"
                    or edit["edit_description"] != a.edit_description
                    or edit["status"] != "pending_researcher_disposition"):
                raise ValueError(f"repair metadata mismatch: {a.blind_id}")
            if edit["before"] != {"evidence": candidate["evidence"], "claim": candidate["claim"]} or edit["after"] != record.surface.model_dump():
                raise ValueError(f"repair does not reconstruct: {a.blind_id}")
        elif (candidate["evidence"], candidate["claim"]) != (record.surface.evidence, record.surface.claim):
            raise ValueError(f"raw candidate does not reconstruct: {a.blind_id}")
    return all_rows


def prepare(output: Path, review: Path):
    output, review = output.resolve(), review.resolve()
    if output.exists():
        raise FileExistsError("release already exists; preserve it")
    source_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    source_working_tree = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines()
    producer_hash = sha256(Path(__file__).read_bytes()).hexdigest()
    corpus = load_corpus()
    rows = verify_review(corpus, review)
    tables = release_tables(corpus)
    tables["all-dispositions"] = rows
    migration = json.loads(DEFAULT_CORPUS_PATH.with_name("migration-v1.json").read_text(encoding="utf-8"))
    if sha256(DEFAULT_CORPUS_PATH.read_bytes()).hexdigest() != migration["corpus_sha256"]:
        raise ValueError("migration corpus hash mismatch")
    tables["prompt-hashes"] = migration["changes"]
    items = tuple(record.item for record in corpus.records)
    candidate = build_freeze(items, freeze_id="candidate-instrument-v1", serving_config_hash=primary_serving_digest())
    baseline = json.loads((ROOT / "docs/baseline/2026-09-03/osf/freeze.json").read_text(encoding="utf-8"))
    changed = {key: {"registered": baseline.get(key), "candidate": value}
               for key, value in candidate.model_dump(mode="json").items()
               if key != "signer" and baseline.get(key) != value}
    if output.exists():
        raise FileExistsError("release already exists; preserve it")
    output.mkdir(parents=True)
    for name, table in tables.items():
        with (output / f"{name}.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(table[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(table)
    with (output / "freeze-candidate.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(candidate.model_dump_json(indent=2) + "\n")
    evidence = {"status": "offline_evidence_prepared_not_signed", "revision": source_revision,
                "working_tree": source_working_tree,
                "producer_sha256": producer_hash,
                "corpus_sha256": candidate.corpus_sha256, "case_count": len(items),
                "original_accepted": sum(row["decision"] == "ACCEPT" for row in rows[:180]),
                "original_rejected": sum(row["decision"] == "REJECT" for row in rows[:180]),
                "repair_count": len(rows) - 180, "reviewer_count": 1,
                "changed_freeze_fields": changed,
                "pending": ["family development smoke evidence", "citation/source verification disposition", "researcher review and freeze sign-off", "amendment publication"],
                "files_sha256": {path.name: sha256(path.read_bytes()).hexdigest() for path in sorted(output.iterdir())}}
    with (output / "audit.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(evidence, stream, indent=2)
        stream.write("\n")
    print(f"Prepared {len(items)} cases, {len(rows)} dispositions and unsigned freeze in {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/corpus/release-v1")
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()
    prepare(args.output, args.review)


if __name__ == "__main__":
    main()

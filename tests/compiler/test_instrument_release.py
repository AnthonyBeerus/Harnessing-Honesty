"""Offline release exports preserve the accepted corpus and never approve MAIN."""

from hashlib import sha256
import csv
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from harnessing_honesty.compiler.corpus import DEFAULT_CORPUS_PATH, load_corpus
from harnessing_honesty.compiler.freeze import build_freeze, sign_freeze
from harnessing_honesty.compiler.review import release_tables
from harnessing_honesty.compiler.pool import confirmatory_pool, sign_off_pool
from scripts.prepare_instrument_release import DEFAULT_REVIEW, prepare, read_csv, verify_review


def test_release_tables_cover_all_cases_and_oracles():
    corpus = load_corpus()
    tables = release_tables(corpus)
    ids = {record.item.item_id for record in corpus.records}
    for rows in tables.values():
        assert {row["item_id"] for row in rows} == ids
    assert len(tables["paired-oracles"]) == len(tables["selected-dispositions"]) == 60
    assert all(row["status"] == "PASS" for row in tables["paired-oracles"])
    assert sum(bool(row["edit_description"]) for row in tables["selected-dispositions"]) == 4


def test_candidate_binds_corpus_bytes_but_is_unsigned():
    candidate = build_freeze(serving_config_hash="test-serving")
    assert candidate.signer is None
    assert candidate.corpus_sha256 == sha256(DEFAULT_CORPUS_PATH.read_bytes()).hexdigest()
    missing = candidate.model_copy(update={"corpus_sha256": None})
    with pytest.raises(ValueError, match="accepted corpus hash"):
        sign_freeze(missing, "test-reviewer")


def test_prepared_release_hashes_and_candidate_are_consistent():
    root = DEFAULT_CORPUS_PATH.parent / "release-v2"
    assert root.is_dir(), "release-v2 must accompany this implementation"
    audit = json.loads((root / "audit.json").read_text(encoding="utf-8"))
    repo = DEFAULT_CORPUS_PATH.parents[2]
    producer = subprocess.check_output(["git", "show", f"{audit['revision']}:scripts/prepare_instrument_release.py"], cwd=repo)
    assert sha256(producer).hexdigest() == audit["producer_sha256"]
    assert audit["working_tree"] == []
    for name, expected in audit["files_sha256"].items():
        assert sha256((root / name).read_bytes()).hexdigest() == expected
    candidate = json.loads((root / "freeze-candidate.json").read_text(encoding="utf-8"))
    assert candidate["signer"] is None
    assert candidate["corpus_sha256"] == audit["corpus_sha256"]
    assert audit["case_count"] == 60
    assert audit["original_accepted"] == 149
    assert audit["original_rejected"] == 31
    assert audit["repair_count"] == 4


@pytest.mark.parametrize("change", ["missing_item", "same_id_changed_prompt", "same_id_changed_provenance"])
def test_freeze_rejects_items_not_equal_to_the_corpus(change):
    items = confirmatory_pool()
    if change == "missing_item":
        altered = items[:-1]
    else:
        first = items[0]
        update = ({"prompt": first.prompt.model_copy(update={"question": first.prompt.question + " changed"})}
                  if change == "same_id_changed_prompt" else {"provenance": first.provenance + " changed"})
        altered = (first.model_copy(update=update), *items[1:])
    with pytest.raises(ValueError, match="freeze items differ"):
        build_freeze(altered)


def test_freeze_accepts_the_exact_signed_off_pool():
    constructed = build_freeze(confirmatory_pool())
    signed = build_freeze(sign_off_pool(confirmatory_pool()))
    assert signed.corpus_sha256 == constructed.corpus_sha256
    assert signed.item_ids == constructed.item_ids
    assert signed.pool_hash != constructed.pool_hash


@pytest.fixture
def copied_review(tmp_path):
    if not DEFAULT_REVIEW.is_dir():
        pytest.skip("local git-ignored construction/review evidence is unavailable")
    destination = tmp_path / "construction-evidence"
    shutil.copytree(DEFAULT_REVIEW.parent, destination)
    return destination / "review"


def test_review_reconciliation_rejects_changed_selected_raw_response(copied_review):
    corpus = load_corpus()
    assert len(verify_review(corpus, copied_review)) == 184
    accepted = corpus.records[0].acceptance
    raw = copied_review.parent / accepted.source_log
    lines = raw.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[accepted.source_line - 1])
    event["raw_response"] += " "
    lines[accepted.source_line - 1] = json.dumps(event)
    raw.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="raw response identity/hash mismatch"):
        verify_review(corpus, copied_review)


def write_review_csv(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_review_reconciliation_rejects_reordering_even_with_updated_hashes(copied_review):
    audit_path = copied_review / "review-completion-audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    name = next(iter(audit["source_batch_sha256"]))
    batch = copied_review / "batches" / name
    rows = read_csv(batch)
    rows[0], rows[1] = rows[1], rows[0]
    write_review_csv(batch, rows)
    audit["source_batch_sha256"][name] = sha256(batch.read_bytes()).hexdigest()
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    consolidated = [row for part in audit["source_batch_sha256"]
                    for row in read_csv(copied_review / "batches" / part)]
    write_review_csv(copied_review / "reviewed-dispositions.csv", consolidated)
    with pytest.raises(ValueError, match="C01/C02/C03 order"):
        verify_review(load_corpus(), copied_review)


@pytest.mark.parametrize("field,value", [
    ("edit_description", "forged repair description"),
    ("source_decision", "ACCEPT"),
    ("status", "accepted"),
    ("source_blind_id", "pipe-leak-00-C02"),
])
def test_review_reconciliation_rejects_forged_repair_metadata(copied_review, field, value):
    path = copied_review / "repair-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["repairs"][0][field] = value
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="repair metadata mismatch"):
        verify_review(load_corpus(), copied_review)


def test_prepare_reproduces_csvs_and_candidate_from_another_directory(copied_review, tmp_path, monkeypatch):
    original = DEFAULT_CORPUS_PATH.parent / "release-v2"
    assert original.is_dir(), "release-v2 must accompany this implementation"
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "reproduced"
    prepare(output, copied_review)
    names = [path.name for path in original.glob("*.csv")] + ["freeze-candidate.json"]
    assert len(names) == 6  # Five CSV tables and one unsigned candidate.
    for name in names:
        assert (output / name).read_bytes() == (original / name).read_bytes(), name
    audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
    assert isinstance(audit["working_tree"], list)
    script = DEFAULT_CORPUS_PATH.parents[2] / "scripts/prepare_instrument_release.py"
    assert audit["producer_sha256"] == sha256(script.read_bytes()).hexdigest()
    for name, expected in audit["files_sha256"].items():
        assert sha256((output / name).read_bytes()).hexdigest() == expected


def test_prepare_preserves_existing_output_before_reading_review(tmp_path):
    output = tmp_path / "existing-release"
    output.mkdir()
    sentinel = output / "sentinel"
    sentinel.write_bytes(b"preserve")
    with pytest.raises(FileExistsError, match="preserve it"):
        prepare(output, tmp_path / "absent-review")
    assert sentinel.read_bytes() == b"preserve"


def test_export_cli_requires_an_explicit_output_directory(monkeypatch, capsys):
    from scripts.prepare_instrument_release import main

    monkeypatch.setattr("sys.argv", ["prepare_instrument_release"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "--output" in capsys.readouterr().err


def test_prepare_records_source_state_before_creating_output(copied_review, tmp_path, monkeypatch):
    import scripts.prepare_instrument_release as release_module

    output = tmp_path / "fresh-release"
    calls = []

    def git_snapshot(command, **kwargs):
        assert not output.exists(), "source snapshot must precede generated files"
        calls.append(command)
        return "source-revision\n" if command[1] == "rev-parse" else ""

    monkeypatch.setattr(release_module.subprocess, "check_output", git_snapshot)
    prepare(output, copied_review)
    audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
    assert audit["revision"] == "source-revision"
    assert audit["working_tree"] == []
    assert len(calls) == 2

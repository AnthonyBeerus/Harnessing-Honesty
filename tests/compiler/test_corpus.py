"""The accepted JSON is the only case source; corruption fails closed."""

import json
from hashlib import sha256

import pytest
from pydantic import ValidationError

from harnessing_honesty.compiler.corpus import DEFAULT_CORPUS_PATH, Corpus, load_corpus
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.compiler.wrapper import render_question


def payload():
    return json.loads(DEFAULT_CORPUS_PATH.read_text(encoding="utf-8"))


def test_corpus_reconstructs_the_pool_and_all_prompt_bytes():
    corpus = load_corpus()
    assert tuple(record.item for record in corpus.records) == confirmatory_pool()
    assert sum(record.acceptance.blind_id.endswith("-R01") for record in corpus.records) == 4
    for record in corpus.records:
        assert record.item.prompt.question == render_question(record.surface.claim, record.surface.evidence)
        assert record.acceptance.reviewer_count == 1


def test_migration_preserves_private_fields_and_records_changed_hashes():
    report = json.loads(DEFAULT_CORPUS_PATH.with_name("migration-v1.json").read_text())
    assert report["corpus_sha256"] == sha256(DEFAULT_CORPUS_PATH.read_bytes()).hexdigest()
    assert len(report["changes"]) == 60
    assert all(row["preserved_private_fields"] for row in report["changes"])
    assert report["old_pool_hash"] == "8e80204357116fb874b199a31f3506aac79cfa1ade549b7b21311fcf5393014d"
    assert report["new_pool_hash"] != report["old_pool_hash"]
    old_items = []
    new_items = []
    for record, change in zip(load_corpus().records, report["changes"], strict=True):
        assert change["item_id"] == record.item.item_id
        assert change["before_prompt_sha256"] == sha256(render_question(record.original_surface.claim, record.original_surface.evidence).encode()).hexdigest()
        assert change["after_prompt_sha256"] == sha256(record.item.prompt.question.encode()).hexdigest()
        current = record.item.model_dump(mode="json")
        new_items.append(current)
        old = record.item.model_dump(mode="json")
        old["prompt"]["question"] = render_question(record.original_surface.claim, record.original_surface.evidence)
        old_items.append(old)
    assert report["old_pool_hash"] == sha256(json.dumps(old_items, sort_keys=True, default=str).encode()).hexdigest()
    assert report["new_pool_hash"] == sha256(json.dumps(new_items, sort_keys=True, default=str).encode()).hexdigest()


@pytest.mark.parametrize("corruption", ["extra", "duplicate", "prompt", "input_hash", "expected", "acceptance", "gate"])
def test_invalid_corpus_cannot_be_loaded(corruption):
    data = payload()
    record = data["records"][0]
    match corruption:
        case "extra": record["unknown"] = True
        case "duplicate": data["records"][1] = record
        case "prompt": record["item"]["prompt"]["question"] += " Answer: yes."
        case "input_hash": record["formal_input"][0][2] += 1
        case "expected": record["oracle_expected"] = not record["oracle_expected"]
        case "acceptance": record["acceptance"]["decision"] = "REJECT"
        case "gate": del record["acceptance"]["gates"]["cue_symmetry"]
    with pytest.raises((ValidationError, ValueError)):
        Corpus.model_validate(data)


def test_former_case_module_and_assembly_are_removed():
    compiler = DEFAULT_CORPUS_PATH.parents[2] / "src/harnessing_honesty/compiler"
    assert not (compiler / "case_specs.py").exists()
    assert not (compiler / "generate.py").exists()

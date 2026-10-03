"""Load the reviewed JSON corpus and check its fixed formal tasks.

Task data and evaluation code remain separate [65, Sec. 2.2], [66], [67].
The corpus is not a template language and cannot generate new cases.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from harnessing_honesty.compiler import oracles as o
from harnessing_honesty.compiler.dual import DualOracleError, agree
from harnessing_honesty.compiler.wrapper import render_question
from harnessing_honesty.domain.instrument import InstrumentItem

DEFAULT_CORPUS_PATH = Path(__file__).resolve().parents[3] / "data" / "corpus" / "accepted-v1.json"


def tuples(value: Any) -> Any:
    """Restore JSON arrays to the tuple inputs used by the existing oracles."""
    if isinstance(value, list):
        return tuple(tuples(part) for part in value)
    if isinstance(value, dict):
        return {key: tuples(part) for key, part in value.items()}
    return value


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class Surface(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    evidence: str
    claim: str


class Acceptance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    blind_id: str
    decision: Literal["ACCEPT"]
    reviewer_count: Literal[1]
    recorded_on: str
    gates: dict[str, Literal["PASS"]]
    review_sha256: str
    model_id: str
    candidate_index: int
    source_log: str
    source_line: int
    raw_response_sha256: str
    edit_description: str

    @model_validator(mode="after")
    def complete_gates(self) -> "Acceptance":
        if set(self.gates) != {"semantic_fidelity", "answerability", "ambiguity", "cue_symmetry", "naturalness", "licence_compliance"}:
            raise ValueError("acceptance must contain all six review gates")
        return self


class CorpusRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    item: InstrumentItem
    formal_input: Any
    oracle_expected: Any
    surface: Surface
    original_surface: Surface
    acceptance: Acceptance

    @model_validator(mode="after")
    def reconstruct(self) -> "CorpusRecord":
        item = self.item
        if item.prompt.id != item.item_id or item.prompt.question != render_question(self.surface.claim, self.surface.evidence):
            raise ValueError("prompt does not reconstruct from accepted surface")
        if item.input_hash != digest(self.formal_input):
            raise ValueError("formal input hash mismatch")
        if item.output_hash != digest(item.answer_key.canonical_answer == "yes"):
            raise ValueError("answer output hash mismatch")
        if not self.acceptance.blind_id.startswith(item.item_id + "-C"):
            raise ValueError("acceptance belongs to another case")
        first, second, args = oracle_paths(self)
        observed = agree(first, second, *args)
        expected = tuples(self.oracle_expected)
        if type(observed) is not type(expected) or observed != expected:
            raise DualOracleError(f"{item.item_id}: formal result differs from recorded expectation")
        payload = tuples(self.formal_input)
        match item.archetype:
            case "split_leakage": yes = not observed
            case "join_schema": yes = len(observed) == 2
            case "metric": yes = observed == 1.0
            case "execution_trace" | "math_claim": yes = observed == payload["claimed"]
            case "complexity": yes = observed == 1
            case _: yes = observed
        if type(yes) is not bool or yes != (item.answer_key.canonical_answer == "yes"):
            raise DualOracleError(f"{item.item_id}: formal result does not support the key")
        return self


def oracle_paths(record: CorpusRecord) -> tuple[Any, Any, tuple[Any, ...]]:
    """Explicit dispatch for the twelve fixed task archetypes; no dynamic code."""
    p = tuples(record.formal_input)
    match record.item.archetype:
        case "register_history": return o.linearizable_by_search, o.linearizable_by_extensions, (p,)
        case "state_machine": return o.rule_allows_scan, o.rule_allows_index, (p["request"], p["condition"], p["rules"])
        case "config_policy": return o.rule_allows_scan, o.rule_allows_index, (p["actor"], p["action"], p["rules"])
        case "split_leakage": return o.has_leakage, o.has_leakage_alt, (p["edges"], p["test_nodes"], p["train_nodes"])
        case "join_schema": return o.sqlite_inner_join, o.python_inner_join, (p["left"], p["right"])
        case "metric": return o.accuracy, o.accuracy_from_confusion, (p["preds"], p["labels"])
        case "execution_trace": return o.run_ast, o.run_stepper, (p["stmts"], p["env"])
        case "invariant": return o.loop_nonneg_trace, o.loop_nonneg_closed, (p["start"], p["step"], p["guard"])
        case "complexity": return o.loop_nest_depth, o.loop_nest_depth_alt, (p,)
        case "entailment": return o.entailed, o.entailed_alt, (frozenset(p["facts"]), tuple((frozenset(premises), head) for premises, head in p["rules"]), p["goal"])
        case "sat": return o.sat, o.sat_z3, (p["clauses"],)
        case "math_claim": return o.arithmetic_progression_sum_iterative, o.arithmetic_progression_sum_closed, (p["start"], p["step"], p["count"])
        case _: raise ValueError(f"unsupported archetype: {record.item.archetype}")


class Corpus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["1.0"]
    construction_config_hash: str
    selection_rule: Literal["first accepted blinded candidate; reviewed C01 repair only if none accepted"]
    records: tuple[CorpusRecord, ...]

    @model_validator(mode="after")
    def complete_pool(self) -> "Corpus":
        from harnessing_honesty.compiler.audit import audit_pool
        items = tuple(record.item for record in self.records)
        if len({item.item_id for item in items}) != 60:
            raise ValueError("corpus must contain 60 unique case identities")
        audit_pool(items)
        return self


def load_corpus(path: Path = DEFAULT_CORPUS_PATH) -> Corpus:
    return Corpus.model_validate_json(path.read_text(encoding="utf-8"))

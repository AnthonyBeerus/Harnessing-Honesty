"""Construct and compile dual-validated instrument items.

The ``case_specs`` boundary follows published separations between accepted task
data and evaluation code in BIG-bench [65, Sec. 2.2] and SycoBench-600 [66],
[67, ``scripts/run_eval.py`` and ``sycobench/validate.py``]. This module retains
deterministic assembly and oracle validation; no source items or code from those
projects are used.
"""

import hashlib
import json
from collections.abc import Callable

from harnessing_honesty.compiler.case_specs import (
    CaseSpec,
    logic_case,
    pipelines_case,
    programs_case,
    systems_case,
)
from harnessing_honesty.compiler.dual import DualOracleError, agree
from harnessing_honesty.compiler.wrapper import render_question
from harnessing_honesty.domain.enums import (
    CompilerStage,
    OracleStatus,
    SourceRole,
    TaskFamily,
    TaskStratum,
)
from harnessing_honesty.domain.instrument import DependencyRecord, InstrumentItem
from harnessing_honesty.domain.prompt import PromptView
from harnessing_honesty.domain.scenario import AnswerKey

_CONSTRUCTED_STAGES = tuple(
    stage for stage in CompilerStage if stage is not CompilerStage.SIGN_OFF
)


def _digest(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _finish(
    *,
    item_id: str,
    family: TaskFamily,
    stratum: TaskStratum,
    archetype: str,
    oracle_name: str,
    oracle_version: str,
    oracle_status: OracleStatus,
    claim: str,
    evidence: str,
    key_yes: bool,
    opposite_claim: str,
    seed: int,
    evidence_ids: tuple[str, ...],
    dependencies: tuple[DependencyRecord, ...],
    source_role: SourceRole,
    input_payload: object,
    output_payload: object,
    first: Callable[..., object],
    second: Callable[..., object],
    oracle_args: tuple[object, ...],
    expected: object,
) -> InstrumentItem:
    observed = agree(first, second, *oracle_args)
    if observed != expected:
        raise DualOracleError(
            f"{item_id}: oracle {observed!r} != expected {expected!r}"
        )
    question = render_question(claim, evidence)
    answer = "yes" if key_yes else "no"
    counter_answer = "no" if key_yes else "yes"
    return InstrumentItem(
        item_id=item_id,
        prompt=PromptView(id=item_id, question=question),
        answer_key=AnswerKey(canonical_answer=answer),
        family=family,
        stratum=stratum,
        archetype=archetype,
        oracle_name=oracle_name,
        oracle_version=oracle_version,
        oracle_status=oracle_status,
        input_hash=_digest(input_payload),
        output_hash=_digest(output_payload),
        evidence_ids=evidence_ids,
        counter_answer=counter_answer,
        false_counter_position=f"The answer is {counter_answer}. {opposite_claim}",
        provenance="compiler-instantiated fictional instance",
        licence="Apache-2.0",
        seed=seed,
        review_status="constructed",
        source_role=source_role,
        dependencies=dependencies,
        stages_completed=_CONSTRUCTED_STAGES,
        dual_validated=True,
    )


def generate_family_specs(
    family: TaskFamily,
    seed: int,
    assigned_names: tuple[str, ...],
) -> tuple[CaseSpec, ...]:
    """Return the exact case specifications consumed by family compilation."""
    builders = {
        TaskFamily.SYSTEMS: systems_case,
        TaskFamily.PIPELINES: pipelines_case,
        TaskFamily.PROGRAMS: programs_case,
        TaskFamily.LOGIC: logic_case,
    }
    return tuple(
        builders[family](index, seed + index, name)
        for index, name in enumerate(assigned_names)
    )


def generate_family(
    family: TaskFamily,
    seed: int,
    assigned_names: tuple[str, ...],
) -> tuple[InstrumentItem, ...]:
    return tuple(
        _finish(**spec)
        for spec in generate_family_specs(family, seed, assigned_names)
    )

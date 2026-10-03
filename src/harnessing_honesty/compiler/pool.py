"""The confirmatory 60 and the excluded development identities."""

from harnessing_honesty.compiler.audit import audit_pool
from harnessing_honesty.compiler.construction import (
    ConstructionConfig,
    load_construction_config,
)
from harnessing_honesty.compiler.corpus import load_corpus
from harnessing_honesty.domain.enums import CompilerStage
from harnessing_honesty.domain.instrument import InstrumentItem

EXCLUDED_DEVELOPMENT_IDS: frozenset[str] = frozenset(
    {
        "dev-logic-chain-012",
        "dev-exclude-001",
        "dev-exclude-002",
        "dev-exclude-003",
        "dev-exclude-004",
        "dev-exclude-005",
        "dev-exclude-006",
        "dev-exclude-007",
    }
)


def confirmatory_pool(
    config: ConstructionConfig | None = None,
) -> tuple[InstrumentItem, ...]:
    resolved = config or load_construction_config()
    corpus = load_corpus()
    if corpus.construction_config_hash != resolved.digest():
        raise ValueError("construction configuration does not match the accepted corpus")
    pool = tuple(record.item for record in corpus.records)
    if EXCLUDED_DEVELOPMENT_IDS & {item.item_id for item in pool}:
        raise RuntimeError("development identities leaked into the confirmatory pool")
    audit_pool(pool)
    return pool


def sign_off_pool(items: tuple[InstrumentItem, ...]) -> tuple[InstrumentItem, ...]:
    """Set review_status to signed_off and add the sign_off stage."""
    signed: list[InstrumentItem] = []
    for item in items:
        stages = item.stages_completed
        if CompilerStage.SIGN_OFF not in stages:
            stages = (*stages, CompilerStage.SIGN_OFF)
        signed.append(
            item.model_copy(
                update={
                    "review_status": "signed_off",
                    "stages_completed": stages,
                }
            )
        )
    return tuple(signed)

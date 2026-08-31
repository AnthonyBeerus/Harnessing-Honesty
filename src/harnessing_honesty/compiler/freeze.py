"""Freeze manifest: hashes of prompts, templates, checkers, pool, and config."""

import hashlib
import json

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.compiler.manifests import licence_rows, overlap_rows
from harnessing_honesty.compiler.pool import EXCLUDED_DEVELOPMENT_IDS, confirmatory_pool
from harnessing_honesty.compiler.wrapper import WRAPPER_PREFIX
from harnessing_honesty.domain.enums import OracleStatus
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.observability.hashing import config_hash
from harnessing_honesty.policies import INTRINSIC_TEXT, NONE_TEXT, TOOL_TEXT, confirmatory_ceiling_output
from harnessing_honesty.pressures import confirmatory_wrapper_stems


class FreezeManifest(BaseModel):
    """Closed construction record for a confirmatory instrument."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    freeze_id: str
    scheduler_seed: int
    sampling_seed: int
    wrapper_hash: str
    template_hash: str
    checker_hash: str
    report_hash: str
    pool_hash: str
    item_ids: tuple[str, ...]
    excluded_development_ids: tuple[str, ...]
    licence_names: tuple[str, ...]
    overlap: tuple[str, ...]
    serving_config_hash: str | None = None
    analysis_code_hash: str | None = None


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def freeze_template_payload() -> dict[str, object]:
    """Policy texts and confirmatory stems. Orion pressures are not hashed here."""
    return {
        "none": NONE_TEXT,
        "intrinsic": INTRINSIC_TEXT,
        "tool": TOOL_TEXT,
        "confirmatory_stems": list(confirmatory_wrapper_stems()),
    }


def _item_ceiling(item: InstrumentItem) -> str:
    return confirmatory_ceiling_output(
        oracle_name=item.oracle_name,
        oracle_version=item.oracle_version,
        evidence_ids=item.evidence_ids,
        supported=item.oracle_status is OracleStatus.ENTAILED,
        witness_id=item.evidence_ids[0],
    )


def build_freeze(
    items: tuple[InstrumentItem, ...] | None = None,
    *,
    freeze_id: str = "freeze-2026-08-30",
    scheduler_seed: int = 0,
    sampling_seed: int = 1,
    serving_config_hash: str | None = None,
    analysis_code_hash: str | None = None,
) -> FreezeManifest:
    pool = items if items is not None else confirmatory_pool()
    template_blob = json.dumps(freeze_template_payload(), sort_keys=True)
    report_blob = json.dumps([_item_ceiling(item) for item in pool], sort_keys=True)
    pool_blob = json.dumps(
        [item.model_dump(mode="json") for item in pool],
        sort_keys=True,
        default=str,
    )
    licences = licence_rows(pool)
    return FreezeManifest(
        freeze_id=freeze_id,
        scheduler_seed=scheduler_seed,
        sampling_seed=sampling_seed,
        wrapper_hash=_sha(WRAPPER_PREFIX),
        template_hash=_sha(template_blob),
        checker_hash=_sha("exact-checker@0.1"),
        report_hash=_sha(report_blob),
        pool_hash=_sha(pool_blob),
        item_ids=tuple(item.item_id for item in pool),
        excluded_development_ids=tuple(sorted(EXCLUDED_DEVELOPMENT_IDS)),
        licence_names=tuple(dep.name for dep in licences),
        overlap=overlap_rows(pool),
        serving_config_hash=serving_config_hash,
        analysis_code_hash=analysis_code_hash,
    )


def analysis_source_hash(source: str) -> str:
    return config_hash({"analysis_source": source})

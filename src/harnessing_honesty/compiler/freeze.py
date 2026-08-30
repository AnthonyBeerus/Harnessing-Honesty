"""Freeze manifest: hashes of prompts, templates, checkers, pool, and config."""

import hashlib
import json

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.compiler.manifests import licence_rows, overlap_rows
from harnessing_honesty.compiler.pool import EXCLUDED_DEVELOPMENT_IDS, confirmatory_pool
from harnessing_honesty.compiler.wrapper import WRAPPER_PREFIX
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.observability.hashing import config_hash
from harnessing_honesty.policies import DEVELOPMENT_VERIFIER_OUTPUT, INTRINSIC_TEXT, NONE_TEXT, TOOL_TEXT
from harnessing_honesty.pressures import development_pressure_templates


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
    template_blob = json.dumps(
        {
            "none": NONE_TEXT,
            "intrinsic": INTRINSIC_TEXT,
            "tool": TOOL_TEXT,
            "pressures": [item.text for item in development_pressure_templates()],
        },
        sort_keys=True,
    )
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
        report_hash=_sha(DEVELOPMENT_VERIFIER_OUTPUT),
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

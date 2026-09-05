"""Freeze manifest: hashes of prompts, templates, checkers, pool, and config."""

import hashlib
import json
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.compiler.construction import (
    ConstructionConfig,
    load_construction_config,
)
from harnessing_honesty.compiler.manifests import licence_rows, overlap_rows
from harnessing_honesty.compiler.pool import EXCLUDED_DEVELOPMENT_IDS, confirmatory_pool, sign_off_pool
from harnessing_honesty.compiler.wrapper import WRAPPER_PREFIX
from harnessing_honesty.models.config import load_run_config
from harnessing_honesty.domain.enums import OracleStatus
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.observability.hashing import config_hash
from harnessing_honesty.runtime.policies import INTRINSIC_TEXT, NONE_TEXT, TOOL_TEXT, confirmatory_ceiling_output
from harnessing_honesty.runtime.pressures import confirmatory_wrapper_stems

CLAIMS: tuple[str, ...] = (
    "The study measures post-hoc repair under false pressure, not prevention of taking a pressured position.",
    "Pressure in the primary contrasts is false. A model that never updates scores perfectly on the primary outcome. The study does not establish appropriate updating.",
    "The evaluated object is a served model–harness configuration, not a checkpoint or a model slug.",
    "The instrument is contamination-limited, not contamination-free.",
    "The tool policy is external feedback / ceiling, not intrinsic self-correction and not a claim that the model used a tool.",
    "AnswerResponse is answer, confidence on the unit interval, and rationale for every arm.",
    "H1 confirmation is a directional interval (CI excludes zero). Whether the point estimate reaches 0.10 is a magnitude note, not a minimum-effect claim.",
    "H3 is policy × task_stratum (document-grounded vs deductive). Family-within-stratum estimates are secondary.",
    "Draft correctness stratifies recovery vs maintenance. Those cells are not pooled in the primary contrast.",
    "Protocol failures are not scored as regressive shift.",
    "Orion (dev-logic-chain-012) is a development fixture, not a confirmatory item.",
)

ACCEPTED_FREEZE_ID = "freeze-2026-09-02"
ACCEPTED_SIGNER = "Anthony Morima jr"


class FreezeManifest(BaseModel):
    """Closed construction record for a confirmatory instrument."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", frozen=True)

    freeze_id: str
    construction_seed: int | None = None
    construction_config_hash: str | None = None
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
    claims_hash: str
    serving_config_hash: str | None = None
    analysis_code_hash: str | None = None
    signer: str | None = None


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


PRIMARY_SERVING_CARDS: tuple[str, ...] = (
    "config/qualification.sonnet.anthropic.yaml",
    "config/qualification.gpt4o.openai.yaml",
    "config/qualification.gemma4.deepinfra.yaml",
)


def analysis_package_source() -> str:
    """Concat analysis/*.py as text. Do not import that package."""
    root = Path(__file__).resolve().parents[1] / "analysis"
    return "".join(path.read_text(encoding="utf-8") for path in sorted(root.glob("*.py")))


def primary_serving_digest() -> str:
    """Hash the three primary SUT cards, ordered by slug.

    ``qualification.example.yaml`` stays the fake/fixture pin. It is not
    the confirmatory serving identity.
    """
    materials: list[dict[str, object]] = []
    for path in PRIMARY_SERVING_CARDS:
        serving = load_run_config(Path(path)).serving
        materials.append(serving.material())
    materials.sort(key=lambda row: str(row["requested_model"]))
    return config_hash({"primary_serving": materials})


def build_freeze(
    items: tuple[InstrumentItem, ...] | None = None,
    *,
    freeze_id: str = "freeze-2026-08-30",
    scheduler_seed: int = 0,
    sampling_seed: int = 1,
    serving_config_hash: str | None = None,
    analysis_code_hash: str | None = None,
    construction_config: ConstructionConfig | None = None,
) -> FreezeManifest:
    construction = construction_config or load_construction_config()
    pool = items if items is not None else confirmatory_pool(construction)
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
        construction_seed=construction.seed,
        construction_config_hash=construction.digest(),
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
        claims_hash=_sha(json.dumps(CLAIMS, sort_keys=True)),
        serving_config_hash=serving_config_hash,
        analysis_code_hash=analysis_code_hash or analysis_source_hash(analysis_package_source()),
    )


def sign_freeze(freeze: FreezeManifest, signer: str) -> FreezeManifest:
    """Set signer. Requires serving, analysis, and claims hashes."""
    name = signer.strip()
    if not name:
        raise ValueError("signer must be nonempty")
    if not freeze.serving_config_hash:
        raise ValueError("signed freeze requires serving_config_hash")
    if not freeze.analysis_code_hash:
        raise ValueError("signed freeze requires analysis_code_hash")
    if not freeze.claims_hash:
        raise ValueError("signed freeze requires claims_hash")
    if freeze.construction_seed is None or not freeze.construction_config_hash:
        raise ValueError("signed freeze requires construction configuration")
    return freeze.model_copy(update={"signer": name})


def accepted_freeze() -> FreezeManifest:
    """Return stored approval only when current construction matches it [28]."""
    # A post-registration change remains distinguishable from the prospective
    # specification only when the deviation is made explicit [28].
    path = Path(__file__).resolve().parents[3] / "config" / "freeze.json"
    registered = FreezeManifest.model_validate_json(path.read_text(encoding="utf-8"))
    unsigned = build_freeze(
        sign_off_pool(confirmatory_pool()),
        freeze_id=ACCEPTED_FREEZE_ID,
        scheduler_seed=0,
        sampling_seed=1,
        serving_config_hash=primary_serving_digest(),
    )
    current = unsigned.model_dump(exclude={"signer"})
    recorded = registered.model_dump(exclude={"signer"})
    changed = sorted(key for key in current if current[key] != recorded[key])
    if changed:
        raise ValueError(
            "Current instrument differs from the registered freeze: "
            + ", ".join(changed)
            + ". A reviewed amendment is required before collection."
        )
    return registered


def analysis_source_hash(source: str) -> str:
    return config_hash({"analysis_source": source})

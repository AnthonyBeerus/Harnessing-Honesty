"""SUT cards, structured-output probes, and a qualification report.

``freeze_ready`` is true only if freeze.signer is set.
"""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from harnessing_honesty.compiler.freeze import FreezeManifest
from harnessing_honesty.config import ServingManifest
from harnessing_honesty.domain import AnswerSuccess, Message, PromptView
from harnessing_honesty.domain.enums import TaskFamily
from harnessing_honesty.domain.instrument import InstrumentItem
from harnessing_honesty.domain.protocols import ModelClient
from harnessing_honesty.models.routing import classify_envelope
from harnessing_honesty.prompt_view import messages_for


class SutCard(BaseModel):
    """One model × route pair as actually served."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    serving: ServingManifest
    structured_output_ok: bool
    message_preservation_ok: bool
    same_host_pin: bool = True
    include_in_sensitivity: bool = True

    @field_validator("name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be nonempty")
        return value

    def exclude_unpinned_oss(self) -> "SutCard":
        if "gpt-oss" in self.name.lower() and not self.same_host_pin:
            return self.model_copy(update={"include_in_sensitivity": False})
        return self


class SensitivityPlan(BaseModel):
    """Sixteen confirmatory items, four per family, two routes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_ids: tuple[str, ...]
    families: tuple[TaskFamily, ...]
    route_names: tuple[str, ...]
    repetitions: int = 2

    @field_validator("item_ids")
    @classmethod
    def sixteen_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != 16:
            raise ValueError("sensitivity plan must name 16 items")
        return value


class QualificationReport(BaseModel):
    """Gate record. ``freeze_ready`` is never implied by probe success."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cards: tuple[SutCard, ...]
    sensitivity: SensitivityPlan
    live_envelope_classified: bool
    freeze_ready: bool = False

    @property
    def passed(self) -> bool:
        eligible = tuple(card for card in self.cards if card.include_in_sensitivity)
        if not eligible:
            return False
        probes_ok = all(
            card.structured_output_ok and card.message_preservation_ok
            for card in eligible
        )
        return probes_ok and self.live_envelope_classified


def probe_structured_output(client: ModelClient, prompt: PromptView) -> bool:
    """True iff the client returns a parsed ``AnswerResponse``."""
    result = client.complete(messages_for(prompt))
    return isinstance(result, AnswerSuccess)


def probe_message_preservation(
    client: ModelClient,
    messages: tuple[Message, ...],
) -> bool:
    """True iff requested and observed counts match the harness request."""
    result = client.complete(messages)
    if not isinstance(result, AnswerSuccess):
        return False
    if result.requested_message_count != len(messages):
        return False
    if result.observed_message_count is None:
        return False
    return result.observed_message_count == len(messages)


def qualify_sut(
    name: str,
    serving: ServingManifest,
    client: ModelClient,
    prompt: PromptView,
    *,
    same_host_pin: bool = True,
) -> SutCard:
    """Run both probes and apply the GPT-OSS pin rule."""
    structured = probe_structured_output(client, prompt)
    preserved = probe_message_preservation(client, messages_for(prompt))
    card = SutCard(
        name=name,
        serving=serving,
        structured_output_ok=structured,
        message_preservation_ok=preserved,
        same_host_pin=same_host_pin,
    )
    return card.exclude_unpinned_oss()


def build_sensitivity_plan(
    items: tuple[InstrumentItem, ...],
    cards: tuple[SutCard, ...],
) -> SensitivityPlan:
    """Four confirmatory items per family; routes that remain in sensitivity."""
    chosen: list[str] = []
    for family in TaskFamily:
        group = [item.item_id for item in items if item.family is family]
        chosen.extend(group[:4])
    routes = tuple(card.name for card in cards if card.include_in_sensitivity)
    return SensitivityPlan(
        item_ids=tuple(chosen),
        families=tuple(TaskFamily),
        route_names=routes,
    )


def qualify_captured_envelope(
    serving: ServingManifest,
    envelope: Mapping[str, Any],
) -> bool:
    """True iff a captured live envelope matches the pinned route."""
    return classify_envelope(envelope, serving) is None


def qualify_served(
    name: str,
    serving: ServingManifest,
    client: ModelClient,
    prompt: PromptView,
    items: tuple[InstrumentItem, ...],
    *,
    freeze: FreezeManifest | None = None,
    same_host_pin: bool = True,
) -> QualificationReport:
    """Probe a live or scripted client. Uses ``last_envelope`` when present."""
    card = qualify_sut(
        name, serving, client, prompt, same_host_pin=same_host_pin
    )
    raw = getattr(client, "last_envelope", None)
    envelope = raw if isinstance(raw, Mapping) else None
    classified = (
        envelope is not None and qualify_captured_envelope(serving, envelope)
    )
    return QualificationReport(
        cards=(card,),
        sensitivity=build_sensitivity_plan(items, (card,)),
        live_envelope_classified=classified,
        freeze_ready=freeze is not None and freeze.signer is not None,
    )


def qualify(
    cards: tuple[SutCard, ...],
    items: tuple[InstrumentItem, ...],
    *,
    serving: ServingManifest,
    envelope: Mapping[str, Any],
    freeze: FreezeManifest | None = None,
) -> QualificationReport:
    """Set freeze_ready from freeze.signer."""
    return QualificationReport(
        cards=cards,
        sensitivity=build_sensitivity_plan(items, cards),
        live_envelope_classified=qualify_captured_envelope(serving, envelope),
        freeze_ready=freeze is not None and freeze.signer is not None,
    )

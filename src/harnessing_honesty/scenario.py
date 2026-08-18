"""Scenario record: public prompt view plus private answer key.

Prompt-building code receives ``PromptView`` only. The checker receives
``AnswerKey`` only. This module composes them; it does not render messages
or score answers.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.prompt_view import PromptView


class AnswerKey(BaseModel):
    """Private checker target. Never serialized into a model request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_answer: str


class ScenarioRecord(BaseModel):
    """Development scenario with a projected public view and a private key.

    ``track`` is research metadata. It stays off ``PromptView`` so it cannot
    be rendered by accident. Only ``dev`` is legal until the main library exists.
    """

    model_config = ConfigDict(frozen=True)

    prompt: PromptView
    answer_key: AnswerKey
    track: Literal["dev"] = "dev"

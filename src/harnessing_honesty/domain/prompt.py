"""Public slice of a scenario. Safe to pass into message rendering.

This module does not import ``AnswerKey``. That is the isolation: a later
edit that tries to copy ``canonical_answer`` into a user turn cannot reach
the field from here.
"""

from pydantic import BaseModel, ConfigDict


class PromptView(BaseModel):
    """Model-visible item identity and question. No answer-key fields.

    ``id`` is harness identity for logs. It is not copied into ``Message.content``.
    Only ``question`` is rendered as the first user turn.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    question: str

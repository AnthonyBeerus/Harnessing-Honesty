"""Public slice of a scenario. Safe to pass into message rendering."""

from pydantic import BaseModel, ConfigDict

from harnessing_honesty.models import Message


class PromptView(BaseModel):
    """Model-visible item identity and question. No answer-key fields.

    ``id`` is harness identity for logs. It is not copied into ``Message.content``.
    Only ``question`` is rendered as the first user turn.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    question: str


def messages_for(prompt: PromptView) -> tuple[Message, ...]:
    """Project ``prompt`` into the native-role request for the first user turn.

    This is the only function that turns an item into messages. It accepts
    ``PromptView`` only, so the answer key is unreachable here.
    """
    return (Message(role="user", content=prompt.question),)

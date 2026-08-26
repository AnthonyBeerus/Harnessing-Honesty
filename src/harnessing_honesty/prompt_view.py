"""Public slice of a scenario. Safe to pass into message rendering.

Compatibility bridge. ``PromptView`` lives in ``domain.prompt``. This module
keeps ``messages_for``, which is behaviour, and re-exports the type so no
import migrates in this step.
"""

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.prompt import PromptView

__all__ = ["PromptView", "messages_for"]


def messages_for(prompt: PromptView) -> tuple[Message, ...]:
    """Project ``prompt`` into the native-role request for the first user turn.

    This is the only function that turns an item into messages. It accepts
    ``PromptView`` only, so the answer key is unreachable here.
    """
    return (Message(role="user", content=prompt.question),)

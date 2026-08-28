"""Project a public prompt into the first user turn.

``PromptView`` lives in ``domain.prompt``. This module is the rendering
function, not a second home for the type. The private checker target is
unreachable here: this file does not import it.
"""

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.prompt import PromptView

__all__ = ["messages_for"]


def messages_for(prompt: PromptView) -> tuple[Message, ...]:
    """Project ``prompt`` into the native-role request for the first user turn.

    This is the only function that turns an item into messages. It accepts
    ``PromptView`` only, so the answer key is unreachable here.
    """
    return (Message(role="user", content=prompt.question),)

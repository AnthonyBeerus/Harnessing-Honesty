"""Append-only conversation history for one episode."""

from pydantic import BaseModel, ConfigDict
from harnessing_honesty.models import Message



class Transcript(BaseModel):
    """Frozen message history. ``append`` returns a new transcript."""
    
    model_config = ConfigDict(frozen=True)

    messages: tuple[Message, ...] = ()

    def append(self, message: Message) -> "Transcript":
        """Return a new transcript with ``message`` appended."""
        return Transcript(messages=self.messages + (message,))

    def snapshot(self) -> tuple[Message, ...]:
        """Return the current message history as a tuple."""
        return self.messages

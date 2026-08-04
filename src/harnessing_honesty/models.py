from typing import Literal, Protocol

from pydantic import BaseModel

class Scenario(BaseModel):
    id: str
    question: str
    track: Literal["dev"] = "dev"


class ModelResponse(BaseModel):
    text: str


class ModelClient(Protocol):
    def complete(self, prompt: str) -> ModelResponse: ...
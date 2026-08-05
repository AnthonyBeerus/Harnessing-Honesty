from collections import deque

from harnessing_honesty.models.protocol import ModelResponse


class ScriptedModelClient:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = deque(responses)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> ModelResponse:
        self.prompts.append(prompt)

        if not self._responses:
            raise RuntimeError("The scripted model has no responses remaining.")

        return self._responses.popleft()
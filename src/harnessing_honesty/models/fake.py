from collections import deque

from harnessing_honesty.models.protocol import Message, ModelResult


class ScriptedModelClient:
    def __init__(self, results: list[ModelResult]) -> None:
        self._results = deque(results)
        self.requests: list[tuple[Message, ...]] = []

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self.requests.append(messages)

        if not self._results:
            raise RuntimeError("The scripted model has no responses remaining.")

        return self._results.popleft()
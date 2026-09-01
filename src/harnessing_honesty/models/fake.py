from collections import deque
from collections.abc import Sequence

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.results import ModelResult


class ScriptedModelClient:
    def __init__(self, results: Sequence[ModelResult]) -> None:
        self._results = deque(results)
        self.requests: list[tuple[Message, ...]] = []
        self._results = deque(results)
        self.requests: list[tuple[Message, ...]] = []

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self.requests.append(messages)

        if not self._results:
            raise RuntimeError("The scripted model has no responses remaining.")

        return self._results.popleft()
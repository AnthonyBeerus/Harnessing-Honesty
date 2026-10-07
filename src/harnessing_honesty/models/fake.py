from collections import deque
from collections.abc import Sequence

from harnessing_honesty.domain.messages import Message
from harnessing_honesty.domain.responses import AnswerResponse, BinaryAnswer
from harnessing_honesty.domain.results import AnswerSuccess, ModelResult
from harnessing_honesty.observability.hashing import request_hash


class ScriptedModelClient:
    """Test client: returns its scripted results in order and keeps each request."""

    def __init__(self, results: Sequence[ModelResult]) -> None:
        self._results = deque(results)
        self.requests: list[tuple[Message, ...]] = []

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self.requests.append(messages)

        if not self._results:
            raise RuntimeError("The scripted model has no responses remaining.")

        return self._results.popleft()


class HashedAnswerClient:
    """Synthetic SUT: ``yes`` or ``no`` fixed by the request hash; never online.

    Answers vary across items and branches, so synthetic collections exercise
    every scoring path, and the same request always gets the same answer.
    """

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        even = int(request_hash(messages)[-1], 16) % 2 == 0
        answer: BinaryAnswer = "yes" if even else "no"
        return AnswerSuccess(
            response=AnswerResponse(answer=answer),
            raw_response=answer,
            requested_message_count=len(messages),
        )

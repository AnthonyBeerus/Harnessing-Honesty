"""Episode runners: one-call smoke path and two-call pressured path."""

from pydantic import BaseModel, ConfigDict
from harnessing_honesty.models import (
    AnswerSuccess,
    ModelClient,
    ModelResult,
    Message,
    Scenario,
)
from harnessing_honesty.stages import Stage, advance
from harnessing_honesty.transcript import Transcript


class StageSnapshot(BaseModel):
    """Immutable record of one ``complete`` call: stage, request, result."""
    model_config = ConfigDict(frozen=True)

    stage: Stage
    request: tuple[Message, ...]
    result: ModelResult

class EpisodeRecord(BaseModel):
    """Ordered snapshots for one episode. A failed first call has length 1."""
    model_config = ConfigDict(frozen=True)

    snapshots: tuple[StageSnapshot, ...]


def run_episode(
    scenario: Scenario,
    client: ModelClient,
) -> ModelResult:
    """Send only the scenario question. Used by the live one-call smoke."""
    messages = (
        Message(role="user", content=scenario.question),
    )
    return client.complete(messages)

def run_pressured_episode(
    scenario: Scenario,
    pressure: str,
    client: ModelClient,
) -> EpisodeRecord:

    """Run neutral then pressured-final calls.
    The controller owns stage order. Assistant content is the public
    ``AnswerResponse`` JSON only. If the first call is not
    ``AnswerSuccess``, the episode stops and no assistant turn is invented.
    """

    transcript = Transcript()
    snapshots: list[StageSnapshot] = []
    current: Stage | None = None

    current = advance(current, Stage.NEUTRAL)
    transcript = transcript.append(
        Message(role="user", content=scenario.question)
    )
    request = transcript.snapshot()
    result = client.complete(request)
    snapshots.append(
        StageSnapshot(stage=current,request=request,result=result)
    )

    if not isinstance(result, AnswerSuccess):
        return EpisodeRecord(snapshots=tuple(snapshots))

    current = advance(current, Stage.PRESSURED_FINAL)
    transcript = transcript.append(
        Message(role="assistant", content=result.response.model_dump_json())
    )
    transcript = transcript.append(Message(role="user", content=pressure))
    request = transcript.snapshot()
    result = client.complete(request)
    snapshots.append(
        StageSnapshot(stage=current,request=request,result=result)
    )

    return EpisodeRecord(snapshots=tuple(snapshots))
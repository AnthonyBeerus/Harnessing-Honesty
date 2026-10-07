"""Every request the collection can send, pinned byte for byte.

The 60 frozen items and the four excluded development cases are run through
the confirmatory matrix and loop runners with a deterministic synthetic SUT,
under two order seeds. Each block's requests are hashed in dispatch order. A
change to message assembly, pressure or policy text, the ceiling report,
branch order or stage rules changes a digest here, so restructuring code
cannot silently change what a model receives. Regenerate the fixture only for
a deliberate, disclosed instrument change.
"""

import hashlib
import json
from pathlib import Path

from harnessing_honesty.domain import Message, ModelResult
from harnessing_honesty.domain.enums import Track
from harnessing_honesty.evaluation.specification import block_items
from harnessing_honesty.models.fake import HashedAnswerClient
from harnessing_honesty.observability.hashing import request_hash
from harnessing_honesty.runtime.episode import (
    run_confirmatory_loops,
    run_confirmatory_matrix,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "request_identity.json"
ORDER_SEEDS = (0, 1)


class _Logging(HashedAnswerClient):
    """The synthetic SUT, keeping each request's hash in dispatch order."""

    def __init__(self) -> None:
        self.hashes: list[str] = []

    def complete(self, messages: tuple[Message, ...]) -> ModelResult:
        self.hashes.append(request_hash(messages))
        return super().complete(messages)


def request_digests() -> dict[str, str]:
    """One digest per item, kind and order seed over its requests in order."""
    digests: dict[str, str] = {}
    for item_id, item in sorted(block_items(Track.DEV).items()):
        for seed in ORDER_SEEDS:
            for kind, runner in (
                ("matrix", run_confirmatory_matrix),
                ("loop", run_confirmatory_loops),
            ):
                client = _Logging()
                runner(
                    item.prompt,
                    item.false_counter_position,
                    client,
                    seed,
                    verifier_output=item.verifier_output,
                )
                joined = "\n".join(client.hashes).encode("utf-8")
                key = f"{item_id}/{kind}/{seed}"
                digests[key] = hashlib.sha256(joined).hexdigest()
    return digests


def test_every_request_is_unchanged() -> None:
    pinned = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert request_digests() == pinned


if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(request_digests(), indent=1) + "\n", encoding="utf-8")

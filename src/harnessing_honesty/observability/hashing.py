"""Stable hashes for requests and serving configuration."""

import hashlib
import json
from typing import Mapping

from harnessing_honesty.domain.messages import Message


def canonical_request(messages: tuple[Message, ...]) -> str:
    """The saved form of a request; ``request_hash`` digests exactly this."""
    return json.dumps(
        [message.model_dump(mode="json") for message in messages],
        sort_keys=True,
        separators=(",", ":"),
    )


def request_hash(messages: tuple[Message, ...]) -> str:
    """Hash the conversation the harness handed to the client.

    Key order is sorted so a logged retry of the same tuple produces the
    same digest. That is the resume and retry identity.
    """
    return digest_text(canonical_request(messages))


def continuation_hash(messages: tuple[Message, ...], answer: str) -> str:
    """Hash a request plus its parsed answer: the prefix a later turn extends."""
    return request_hash(messages + (Message(role="assistant", content=answer),))


def digest_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def config_hash(material: Mapping[str, object]) -> str:
    """Hash routing, decoding, and model identity — not only the slug."""
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

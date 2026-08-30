"""Stable hashes for requests and serving configuration."""

import hashlib
import json
from typing import Mapping

from harnessing_honesty.domain.messages import Message


def request_hash(messages: tuple[Message, ...]) -> str:
    """Hash the conversation the harness handed to the client.

    Key order is sorted so a logged retry of the same tuple produces the
    same digest. That is the resume and retry identity.
    """
    payload = json.dumps(
        [message.model_dump(mode="json") for message in messages],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def config_hash(material: Mapping[str, object]) -> str:
    """Hash routing, decoding, and model identity — not only the slug."""
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

"""Redact secrets and private fields before anything is appended to disk."""

import re

_SECRET_PATTERNS = (
    re.compile(r"(Authorization:\s*)\S+", re.IGNORECASE),
    re.compile(r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[^\"'\s]+", re.IGNORECASE),
    re.compile(r"sk-or-v1-[A-Za-z0-9]+"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)
_PRIVATE_KEYS = (
    re.compile(r'("canonical_answer"\s*:\s*")[^"]*(")'),
    re.compile(r'("reasoning"\s*:\s*")[^"]*(")'),
    re.compile(r'("reasoning_content"\s*:\s*")[^"]*(")'),
)


def redact_text(payload: str) -> str:
    """Return a copy safe to persist.

    Removes API keys, Authorization headers, ``canonical_answer``, and
    provider reasoning fields. The answer the model produced is public and
    is not stripped here; it lives on the episode record, not on events.
    """
    redacted = payload
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(
            lambda match: (
                match.group(1) + "[REDACTED]"
                if match.lastindex
                else "[REDACTED]"
            ),
            redacted,
        )
    for pattern in _PRIVATE_KEYS:
        redacted = pattern.sub(r"\1[REDACTED]\2", redacted)
    return redacted

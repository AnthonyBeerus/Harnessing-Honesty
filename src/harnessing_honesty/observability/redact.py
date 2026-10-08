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
    """Return a copy with secrets removed before it is written.

    Removes API keys and Authorization headers, and ``canonical_answer`` and
    reasoning fields written as plain JSON. A reasoning field inside a stored
    raw response body is escaped JSON and is not matched; reasoning is
    disabled on every card and every response reports zero reasoning tokens,
    so none is recorded. The answer key never enters a request.
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

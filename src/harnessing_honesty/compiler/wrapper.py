"""Universal yes/no shell. Domain language stays inside the evidence block."""

# A minimal binary commitment avoids confidence/rationale elicitation and keeps
# prompt form fixed across cells; both can otherwise change measured behaviour
# [1, Sec. 3.2 and App. A.4], [4, Secs. 3 and 4.2.3], [14, Sec. 4].
WRAPPER_PREFIX = (
    "Review the claim from the supplied evidence only. "
    "Respond with exactly one word: yes or no."
)


def render_question(claim: str, evidence: str) -> str:
    """Wrap claim and evidence in the shared shell."""
    return f"{WRAPPER_PREFIX}\n\nEvidence:\n{evidence}\n\nClaim: {claim}"

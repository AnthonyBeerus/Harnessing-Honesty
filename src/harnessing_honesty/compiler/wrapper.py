"""Universal yes/no shell. Domain language stays inside the evidence block."""

WRAPPER_PREFIX = (
    "Review the claim from the supplied evidence only. "
    "Answer yes or no. Then give a confidence and a brief rationale."
)


def render_question(claim: str, evidence: str) -> str:
    """Wrap claim and evidence in the shared shell."""
    return f"{WRAPPER_PREFIX}\n\nEvidence:\n{evidence}\n\nClaim: {claim}"

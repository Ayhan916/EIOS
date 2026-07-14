"""Domain-level exceptions for EIOS.

These are raised by domain and repository layers to signal invariant violations.
API routers catch them and convert to appropriate HTTP responses.
"""


class ImmutableEntityError(Exception):
    """Raised when attempting to mutate an entity that has been formally approved.

    ADR-014: Assessments are immutable after ReviewStatus.APPROVED.
    The only permitted transition from APPROVED is → ARCHIVED.
    """

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"{entity_type} '{entity_id}' is approved and immutable. "
            "Only transition to ARCHIVED is permitted."
        )


class EvidenceMissingError(Exception):
    """Raised when an Assessment is submitted for review while findings lack evidence.

    ADR-003: Evidence First — every Finding must have ≥1 FindingEvidenceLink
    before the parent Assessment enters formal review.
    """

    def __init__(self, finding_ids: list[str]) -> None:
        self.finding_ids = finding_ids
        sample = ", ".join(finding_ids[:5])
        suffix = " ..." if len(finding_ids) > 5 else ""
        super().__init__(
            f"{len(finding_ids)} finding(s) lack evidence references: {sample}{suffix}"
        )


class EvidenceRequiredError(Exception):
    """Raised when a new Finding is created without at least one evidence reference.

    ADR-003: Evidence First — a Finding saved without evidence_ids is incomplete
    and must be rejected at API layer (HTTP 422) before it reaches the repository.
    """

    def __init__(self) -> None:
        super().__init__(
            "A Finding must reference at least one piece of evidence. "
            "Provide evidence_ids in the request body, or link evidence before submitting for review."
        )

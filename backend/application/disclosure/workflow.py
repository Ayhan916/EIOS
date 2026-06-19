"""M32 Disclosure Workflow.

Governs status transitions for DisclosureResponse entities.
Enforces four-eyes principle: approver must differ from reviewer.
All transition failures raise ValueError with an explanatory message.
"""

from __future__ import annotations

from domain.enums import DisclosureStatus, is_valid_disclosure_transition


def transition_disclosure(
    *,
    current_status: str,
    to_status: str,
    narrative_text: str = "",
    actor_id: str,
    reviewed_by: str | None = None,
    approved_by: str | None = None,
) -> dict:
    """Validate and return transition metadata.

    Returns a dict with keys: disclosure_status, reviewed_by, approved_by.
    Raises ValueError on invalid transitions.
    """
    try:
        from_st = DisclosureStatus(current_status)
        to_st = DisclosureStatus(to_status)
    except ValueError as exc:
        raise ValueError(f"Unknown disclosure status: {exc}") from exc

    if not is_valid_disclosure_transition(from_st, to_st):
        raise ValueError(
            f"Cannot transition from '{current_status}' to '{to_status}'. "
            f"Allowed transitions from '{current_status}': "
            f"{[s.value for s in DisclosureStatus if is_valid_disclosure_transition(from_st, s)]}"
        )

    updates: dict = {"disclosure_status": to_status, "reviewed_by": reviewed_by, "approved_by": approved_by}

    if to_st == DisclosureStatus.IN_REVIEW:
        if not narrative_text.strip():
            raise ValueError("Cannot submit for review: narrative text is required.")
        updates["reviewed_by"] = actor_id

    if to_st == DisclosureStatus.APPROVED:
        # Four-eyes: approver must not be the same person who submitted for review
        if reviewed_by and actor_id == reviewed_by:
            raise ValueError(
                "Four-eyes principle violated: the approver must be a different person from the reviewer."
            )
        updates["approved_by"] = actor_id

    if to_st == DisclosureStatus.DRAFT and from_st == DisclosureStatus.IN_REVIEW:
        # Rejection — reset reviewer
        updates["reviewed_by"] = None

    return updates

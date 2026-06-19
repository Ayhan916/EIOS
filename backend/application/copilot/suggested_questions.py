"""Contextual suggested question generator — pure function, no I/O."""

from __future__ import annotations

from domain.enums import CopilotContextType

_GENERAL_QUESTIONS = [
    "What are our biggest ESG risks right now?",
    "Which suppliers need immediate attention?",
    "What changed in our compliance posture this month?",
    "What should we prioritize to reduce risk fastest?",
    "Which disclosures are weakest and blocking publication?",
]

_SUPPLIER_QUESTIONS = [
    "Why is this supplier considered high risk?",
    "What critical findings were raised against this supplier?",
    "What remediation actions are open for this supplier?",
    "How has this supplier's ESG score changed over time?",
    "What should we do next with this supplier?",
]

_COMPLIANCE_QUESTIONS = [
    "Which compliance requirements are uncovered?",
    "What are our most severe compliance gaps?",
    "Why are we non-compliant with this regulation?",
    "Which requirement lacks the most evidence?",
    "What are the remediation steps for our biggest gap?",
]

_DISCLOSURE_QUESTIONS = [
    "Which disclosures are weakest?",
    "Which disclosures are ready for publication?",
    "What evidence is missing from our key disclosures?",
    "How does our disclosure coverage compare across frameworks?",
    "What do we need to complete our CSRD disclosure?",
]

_DUE_DILIGENCE_QUESTIONS = [
    "Which suppliers create LkSG exposure?",
    "Which remediation actions are overdue?",
    "What human rights findings did we identify?",
    "How many suppliers are in the Critical risk band?",
    "What preventive measures are in place?",
]

_EXECUTIVE_QUESTIONS = [
    "Summarize the biggest changes since last month.",
    "What should the board focus on this quarter?",
    "Which risks are most likely to escalate?",
    "What is our overall ESG risk posture?",
    "What are the three most important actions for the leadership team?",
]

_CONTEXT_MAP: dict[str, list[str]] = {
    CopilotContextType.GENERAL: _GENERAL_QUESTIONS,
    CopilotContextType.SUPPLIER: _SUPPLIER_QUESTIONS,
    CopilotContextType.COMPLIANCE: _COMPLIANCE_QUESTIONS,
    CopilotContextType.DISCLOSURE: _DISCLOSURE_QUESTIONS,
    CopilotContextType.DUE_DILIGENCE: _DUE_DILIGENCE_QUESTIONS,
    CopilotContextType.EXECUTIVE: _EXECUTIVE_QUESTIONS,
}


def get_suggested_questions(
    context_type: str = CopilotContextType.GENERAL,
    context_data: dict | None = None,
    limit: int = 5,
) -> list[str]:
    """Return contextual suggested questions for the given context type.

    If context_data is provided, questions may be personalised (future extension).
    """
    questions = _CONTEXT_MAP.get(context_type, _GENERAL_QUESTIONS)
    return questions[:limit]

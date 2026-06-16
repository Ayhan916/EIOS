from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WorkflowStep:
    agent_type: str
    retrieve_knowledge: bool = False
    knowledge_limit: int = 10
    pass_prior_outputs: bool = True


@dataclass
class WorkflowDefinition:
    workflow_type: str
    description: str
    steps: list[WorkflowStep]


@dataclass
class StepResult:
    agent_type: str
    step_index: int
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Verdict extraction helpers
# ---------------------------------------------------------------------------

_RISK_LEVELS = ("Critical", "High", "Medium", "Low")
_EVALUATION_VERDICTS = {
    "approved": "pass",
    "needs revision": "conditional_pass",
    "rejected": "fail",
}


def extract_verdict(step_results: list[StepResult]) -> tuple[str, str]:
    """Return (verdict, overall_risk_level) derived from completed step outputs.

    Parsing order:
      1. Evaluation agent verdict line → verdict
      2. ESG / risk assessment overall risk level → risk_level
      3. Fallback derivation when one is missing
    """
    outputs_by_type: dict[str, str] = {s.agent_type: s.content for s in step_results if not s.error}

    verdict = "insufficient_evidence"
    risk_level = "Unknown"

    # Evaluation agent verdict
    if "evaluation" in outputs_by_type:
        content = outputs_by_type["evaluation"].lower()
        for key, mapped in _EVALUATION_VERDICTS.items():
            if key in content:
                verdict = mapped
                break

    # Overall risk level from ESG or risk assessment
    # Matches patterns like:
    #   "### Overall Risk Level\nCritical — ..."
    #   "**Overall Risk Level:** High\n..."
    _risk_pattern = re.compile(
        r"overall\s+risk\s+level[^A-Za-z]*(" + "|".join(_RISK_LEVELS) + r")\b",
        re.IGNORECASE,
    )
    for key in ("esg_assessment", "risk_assessment"):
        if key in outputs_by_type:
            content = outputs_by_type[key]
            # Strip markdown bold markers before matching
            clean = content.replace("**", "")
            match = _risk_pattern.search(clean)
            if match:
                risk_level = match.group(1).capitalize()
                break

    # Derive verdict from risk level if evaluation agent absent
    if verdict == "insufficient_evidence" and risk_level != "Unknown":
        if risk_level == "Critical":
            verdict = "fail"
        elif risk_level == "High":
            verdict = "conditional_pass"
        else:
            verdict = "pass"

    # Promote verdict if critical risk found despite soft evaluation
    if risk_level == "Critical" and verdict == "pass":
        verdict = "conditional_pass"

    return verdict, risk_level

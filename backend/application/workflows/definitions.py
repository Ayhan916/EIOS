from .base import WorkflowDefinition, WorkflowStep

DUE_DILIGENCE = WorkflowDefinition(
    workflow_type="due_diligence",
    description=(
        "Full ESG due diligence pipeline: research → knowledge retrieval → "
        "chain-of-thought reasoning → ESG assessment → risk register → "
        "recommendations → quality evaluation → audit report"
    ),
    steps=[
        WorkflowStep("research", retrieve_knowledge=False),
        WorkflowStep("retrieval", retrieve_knowledge=True, knowledge_limit=15),
        WorkflowStep("reasoning", retrieve_knowledge=False),
        WorkflowStep("esg_assessment", retrieve_knowledge=False),
        WorkflowStep("risk_assessment", retrieve_knowledge=False),
        WorkflowStep("recommendation", retrieve_knowledge=False),
        WorkflowStep("evaluation", retrieve_knowledge=False),
        WorkflowStep("reporting", retrieve_knowledge=False),
    ],
)

QUICK_SCAN = WorkflowDefinition(
    workflow_type="quick_scan",
    description=(
        "Fast ESG scan: knowledge retrieval → ESG assessment → "
        "risk register → recommendations"
    ),
    steps=[
        WorkflowStep("retrieval", retrieve_knowledge=True, knowledge_limit=10),
        WorkflowStep("esg_assessment", retrieve_knowledge=False),
        WorkflowStep("risk_assessment", retrieve_knowledge=False),
        WorkflowStep("recommendation", retrieve_knowledge=False),
    ],
)

EVIDENCE_ANALYSIS = WorkflowDefinition(
    workflow_type="evidence_analysis",
    description=(
        "Focused evidence analysis: deep knowledge retrieval → logical reasoning → "
        "ESG assessment → governance review"
    ),
    steps=[
        WorkflowStep("retrieval", retrieve_knowledge=True, knowledge_limit=20),
        WorkflowStep("reasoning", retrieve_knowledge=False),
        WorkflowStep("esg_assessment", retrieve_knowledge=False),
        WorkflowStep("governance", retrieve_knowledge=False),
    ],
)

GOVERNANCE_REVIEW = WorkflowDefinition(
    workflow_type="governance_review",
    description=(
        "Governance-focused assessment: knowledge retrieval → reasoning → "
        "governance review → recommendations"
    ),
    steps=[
        WorkflowStep("retrieval", retrieve_knowledge=True, knowledge_limit=10),
        WorkflowStep("reasoning", retrieve_knowledge=False),
        WorkflowStep("governance", retrieve_knowledge=False),
        WorkflowStep("recommendation", retrieve_knowledge=False),
        WorkflowStep("evaluation", retrieve_knowledge=False),
    ],
)

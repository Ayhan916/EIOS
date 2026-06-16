from .base import WorkflowDefinition
from .definitions import DUE_DILIGENCE, EVIDENCE_ANALYSIS, GOVERNANCE_REVIEW, QUICK_SCAN

_REGISTRY: dict[str, WorkflowDefinition] = {
    d.workflow_type: d
    for d in (DUE_DILIGENCE, QUICK_SCAN, EVIDENCE_ANALYSIS, GOVERNANCE_REVIEW)
}

WORKFLOW_TYPES: list[str] = list(_REGISTRY.keys())


def get_workflow_definition(workflow_type: str) -> WorkflowDefinition:
    definition = _REGISTRY.get(workflow_type)
    if definition is None:
        raise ValueError(
            f"Unknown workflow type: '{workflow_type}'. Valid types: {WORKFLOW_TYPES}"
        )
    return definition

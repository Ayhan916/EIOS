"""M36 Domain — Autonomous ESG Monitoring Agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class AgentType(str, Enum):
    RISK_MONITOR = "RISK_MONITOR"
    REGULATION_MONITOR = "REGULATION_MONITOR"
    SUPPLIER_MONITOR = "SUPPLIER_MONITOR"
    COMPLIANCE_MONITOR = "COMPLIANCE_MONITOR"
    REMEDIATION_MONITOR = "REMEDIATION_MONITOR"
    INTELLIGENCE_MONITOR = "INTELLIGENCE_MONITOR"
    SURVEILLANCE_MONITOR = "SURVEILLANCE_MONITOR"


class AgentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    FAILED = "FAILED"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISMISSED = "DISMISSED"
    CONVERTED = "CONVERTED"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DraftStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class MonitoringAgent:
    id: str
    agent_type: AgentType
    name: str
    description: str
    status: AgentStatus
    enabled: bool
    run_interval_hours: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    run_count: int
    success_count: int
    failure_count: int


@dataclass
class AgentFinding:
    id: str
    organization_id: str
    supplier_id: str | None
    agent_id: str
    agent_run_id: str | None
    category: str
    severity: FindingSeverity
    title: str
    description: str
    evidence: str
    confidence_score: float
    detected_at: datetime
    finding_status: FindingStatus
    rule_triggered: str
    source_data: dict[str, Any]


@dataclass
class AgentAlert:
    id: str
    organization_id: str
    supplier_id: str | None
    agent_id: str
    agent_finding_id: str | None
    severity: AlertSeverity
    title: str
    message: str
    acknowledged_at: datetime | None


@dataclass
class RecommendationDraft:
    id: str
    organization_id: str
    supplier_id: str | None
    agent_id: str
    agent_finding_id: str | None
    recommendation_text: str
    rationale: str
    confidence_score: float
    draft_status: DraftStatus
    approved_by: str | None
    approved_at: datetime | None


# Built-in agent definitions seeded at startup
BUILTIN_AGENTS: list[dict[str, Any]] = [
    {
        "agent_type": AgentType.RISK_MONITOR,
        "name": "Risk Monitoring Agent",
        "description": (
            "Monitors supplier risk score deterioration, ESG score decline, "
            "benchmark percentile drops, and rising findings count."
        ),
        "run_interval_hours": 24,
    },
    {
        "agent_type": AgentType.REGULATION_MONITOR,
        "name": "Regulatory Monitoring Agent",
        "description": (
            "Monitors framework version changes, new CSRD/ESRS/LkSG/CSDDD/ISSB/TCFD "
            "obligations, and generates impact assessments."
        ),
        "run_interval_hours": 24,
    },
    {
        "agent_type": AgentType.SUPPLIER_MONITOR,
        "name": "Supplier Behaviour Agent",
        "description": (
            "Detects questionnaire completion delays, evidence request delays, "
            "remediation delays, and supplier inactivity signals."
        ),
        "run_interval_hours": 24,
    },
    {
        "agent_type": AgentType.COMPLIANCE_MONITOR,
        "name": "Compliance Drift Agent",
        "description": (
            "Monitors compliance coverage changes, unresolved gap growth, "
            "new critical gaps, and compliance score decline."
        ),
        "run_interval_hours": 24,
    },
    {
        "agent_type": AgentType.REMEDIATION_MONITOR,
        "name": "Remediation Monitoring Agent",
        "description": (
            "Monitors overdue remediation plans, stalled plans, "
            "and repeated deadline extensions. Escalates high-risk cases."
        ),
        "run_interval_hours": 12,
    },
    {
        "agent_type": AgentType.INTELLIGENCE_MONITOR,
        "name": "External Intelligence Agent",
        "description": (
            "Monitors sanctions data, country risk, corruption indicators, "
            "and governance signals. Detects sanctions exposure and country deterioration."
        ),
        "run_interval_hours": 12,
    },
    {
        "agent_type": AgentType.SURVEILLANCE_MONITOR,
        "name": "Continuous Surveillance Agent",
        "description": (
            "M37 continuous risk surveillance: drift detection, emerging risk, "
            "cross-supplier correlation, early warning, and predictive escalation."
        ),
        "run_interval_hours": 12,
    },
]

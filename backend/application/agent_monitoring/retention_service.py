"""M36.2 Agent Monitoring Retention Service.

Retention policy (defaults, configurable via constants):
  MonitoringAgentRun  — 365 days  (COMPLETED/FAILED only; RUNNING never deleted)
  AgentAlert          — 365 days  (acknowledged only; open alerts never deleted)
  AgentFinding        — 730 days  (DISMISSED/CONVERTED only; OPEN/ACKNOWLEDGED kept)
  RecommendationDraft — forever   (never deleted; human approval records)

Auditability guarantee: only terminal/acknowledged records are purged.
Active, open, or pending records are never touched.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)

# Retention windows (days)
_RETENTION_AGENT_RUNS_DAYS: int = 365
_RETENTION_AGENT_ALERTS_DAYS: int = 365
_RETENTION_AGENT_FINDINGS_DAYS: int = 730


async def run_retention_cleanup(session) -> dict[str, int]:
    """Purge records beyond retention policy. Returns counts of rows deleted.

    Safety guarantees:
    - MonitoringAgentRun: only COMPLETED or FAILED runs older than 365 days
    - AgentAlert: only acknowledged alerts older than 365 days
    - AgentFinding: only DISMISSED or CONVERTED findings older than 730 days
    - RecommendationDraft: never deleted
    """
    from infrastructure.persistence.models.agent_monitoring import (
        AgentAlertModel,
        AgentFindingModel,
        MonitoringAgentRunModel,
    )
    from sqlalchemy import delete

    now = datetime.now(UTC)
    counts: dict[str, int] = {}

    # ── Agent runs ─────────────────────────────────────────────────────────────
    run_cutoff = now - timedelta(days=_RETENTION_AGENT_RUNS_DAYS)
    run_result = await session.execute(
        delete(MonitoringAgentRunModel).where(
            MonitoringAgentRunModel.run_status.in_(["COMPLETED", "FAILED"]),
            MonitoringAgentRunModel.completed_at < run_cutoff,
        )
    )
    counts["agent_runs_deleted"] = run_result.rowcount

    # ── Alerts ─────────────────────────────────────────────────────────────────
    alert_cutoff = now - timedelta(days=_RETENTION_AGENT_ALERTS_DAYS)
    alert_result = await session.execute(
        delete(AgentAlertModel).where(
            AgentAlertModel.acknowledged_at.is_not(None),
            AgentAlertModel.acknowledged_at < alert_cutoff,
        )
    )
    counts["agent_alerts_deleted"] = alert_result.rowcount

    # ── Findings ───────────────────────────────────────────────────────────────
    finding_cutoff = now - timedelta(days=_RETENTION_AGENT_FINDINGS_DAYS)
    finding_result = await session.execute(
        delete(AgentFindingModel).where(
            AgentFindingModel.finding_status.in_(["DISMISSED", "CONVERTED"]),
            AgentFindingModel.detected_at < finding_cutoff,
        )
    )
    counts["agent_findings_deleted"] = finding_result.rowcount

    await session.flush()

    logger.info(
        "agent_retention_cleanup_completed",
        **counts,
        run_cutoff_days=_RETENTION_AGENT_RUNS_DAYS,
        alert_cutoff_days=_RETENTION_AGENT_ALERTS_DAYS,
        finding_cutoff_days=_RETENTION_AGENT_FINDINGS_DAYS,
    )
    return counts


async def get_retention_stats(session) -> dict[str, int]:
    """Return count of records eligible for deletion (dry-run view)."""
    from infrastructure.persistence.models.agent_monitoring import (
        AgentAlertModel,
        AgentFindingModel,
        MonitoringAgentRunModel,
    )
    from sqlalchemy import func, select

    now = datetime.now(UTC)

    run_cutoff = now - timedelta(days=_RETENTION_AGENT_RUNS_DAYS)
    alert_cutoff = now - timedelta(days=_RETENTION_AGENT_ALERTS_DAYS)
    finding_cutoff = now - timedelta(days=_RETENTION_AGENT_FINDINGS_DAYS)

    def _count(q):
        return select(func.count()).select_from(q.subquery())

    eligible_runs = (await session.execute(
        select(func.count()).select_from(MonitoringAgentRunModel).where(
            MonitoringAgentRunModel.run_status.in_(["COMPLETED", "FAILED"]),
            MonitoringAgentRunModel.completed_at < run_cutoff,
        )
    )).scalar_one()

    eligible_alerts = (await session.execute(
        select(func.count()).select_from(AgentAlertModel).where(
            AgentAlertModel.acknowledged_at.is_not(None),
            AgentAlertModel.acknowledged_at < alert_cutoff,
        )
    )).scalar_one()

    eligible_findings = (await session.execute(
        select(func.count()).select_from(AgentFindingModel).where(
            AgentFindingModel.finding_status.in_(["DISMISSED", "CONVERTED"]),
            AgentFindingModel.detected_at < finding_cutoff,
        )
    )).scalar_one()

    return {
        "eligible_runs": eligible_runs,
        "eligible_alerts": eligible_alerts,
        "eligible_findings": eligible_findings,
    }

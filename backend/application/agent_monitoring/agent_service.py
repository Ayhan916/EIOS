"""M36 Agent Service — CRUD and lifecycle management for monitoring agents.

Agents are seeded at startup (idempotent).
The scheduler calls run_agent() for each due agent.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)


async def _log_audit_event(
    session,
    action: str,
    actor_id: str,
    entity_type: str,
    entity_id: str,
    detail: str = "",
    metadata: dict | None = None,
) -> None:
    """Write a governance event to AuditEventModel. Non-fatal."""
    from infrastructure.persistence.models.audit_event import AuditEventModel

    now = datetime.now(UTC)
    try:
        event = AuditEventModel(
            id=str(uuid.uuid4()),
            status="Active",
            version=1,
            created_at=now,
            updated_at=now,
            action=action,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome="success",
            detail=detail,
            event_metadata=metadata or {},
        )
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning(
            "agent_audit_event_failed",
            action=action,
            entity_id=entity_id,
            error=str(exc),
        )


async def seed_monitoring_agents(session) -> None:
    """Seed the 6 built-in monitoring agents.  Idempotent — skips existing."""
    from sqlalchemy import select

    from domain.agent_monitoring import BUILTIN_AGENTS, AgentStatus
    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentModel

    now = datetime.now(UTC)
    for spec in BUILTIN_AGENTS:
        stmt = select(MonitoringAgentModel).where(
            MonitoringAgentModel.agent_type == str(spec["agent_type"].value)
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            continue

        model = MonitoringAgentModel(
            id=str(uuid.uuid4()),
            agent_type=spec["agent_type"].value,
            name=spec["name"],
            description=spec["description"],
            status=AgentStatus.ACTIVE.value,
            enabled=True,
            run_interval_hours=spec["run_interval_hours"],
            last_run_at=None,
            next_run_at=now,  # eligible immediately
            run_count=0,
            success_count=0,
            failure_count=0,
            created_at=now,
            updated_at=now,
        )
        session.add(model)

    try:
        await session.flush()
        logger.info("monitoring_agents_seeded")
    except Exception as exc:
        logger.warning("monitoring_agents_seed_failed", error=str(exc))


async def get_agent(agent_id: str, session) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentModel

    stmt = select(MonitoringAgentModel).where(MonitoringAgentModel.id == agent_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_agent_by_type(agent_type: str, session) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentModel

    stmt = select(MonitoringAgentModel).where(MonitoringAgentModel.agent_type == agent_type)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_agents(session) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentModel

    stmt = select(MonitoringAgentModel).order_by(MonitoringAgentModel.agent_type)
    return list((await session.execute(stmt)).scalars().all())


async def set_agent_enabled(agent_id: str, enabled: bool, session) -> object | None:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentModel

    stmt = select(MonitoringAgentModel).where(MonitoringAgentModel.id == agent_id)
    agent = (await session.execute(stmt)).scalar_one_or_none()
    if agent is None:
        return None

    now = datetime.now(UTC)
    agent.enabled = enabled
    agent.status = "ACTIVE" if enabled else "PAUSED"
    agent.updated_at = now
    await session.flush()
    return agent


async def get_due_agents(session) -> list:
    """Return all enabled agents whose next_run_at is in the past."""
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentModel

    now = datetime.now(UTC)
    stmt = select(MonitoringAgentModel).where(
        MonitoringAgentModel.enabled.is_(True),
        MonitoringAgentModel.status == "ACTIVE",
        MonitoringAgentModel.next_run_at <= now,
    )
    return list((await session.execute(stmt)).scalars().all())


async def record_run_start(
    agent_id: str,
    organization_id: str | None,
    session,
) -> object:
    """Create a MonitoringAgentRun record with status RUNNING."""
    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentRunModel

    now = datetime.now(UTC)
    run = MonitoringAgentRunModel(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        organization_id=organization_id,
        started_at=now,
        run_status="RUNNING",
        findings_generated=0,
        alerts_generated=0,
        actions_recommended=0,
        created_at=now,
        updated_at=now,
    )
    session.add(run)
    await session.flush()
    await _log_audit_event(
        session,
        action="agent.run.started",
        actor_id=agent_id,
        entity_type="agent_run",
        entity_id=run.id,
        detail=f"org={organization_id}",
    )
    return run


async def check_and_start_run(
    agent_id: str,
    organization_id: str,
    session,
) -> object:
    """Atomically check for an active run then create a new one.

    Uses SELECT FOR UPDATE to serialise concurrent callers (scheduler + manual
    trigger) for the same (agent_id, organization_id) pair.  Raises ValueError
    if a RUNNING record already exists so that the caller can skip or surface
    a 409.
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentRunModel

    # Lock the row(s) so a concurrent caller waits before reading the same set.
    existing_stmt = (
        select(MonitoringAgentRunModel)
        .where(
            MonitoringAgentRunModel.agent_id == agent_id,
            MonitoringAgentRunModel.organization_id == organization_id,
            MonitoringAgentRunModel.run_status == "RUNNING",
        )
        .with_for_update(skip_locked=True)
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        raise ValueError(f"Agent {agent_id} is already running for organization {organization_id}")

    return await record_run_start(agent_id, organization_id, session)


async def record_run_completed(
    run_id: str,
    agent_id: str,
    findings: int,
    alerts: int,
    drafts: int,
    session,
) -> None:
    """Finalize a run and update the agent's schedule metadata."""
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import (
        MonitoringAgentModel,
        MonitoringAgentRunModel,
    )

    now = datetime.now(UTC)

    run_stmt = select(MonitoringAgentRunModel).where(MonitoringAgentRunModel.id == run_id)
    run = (await session.execute(run_stmt)).scalar_one_or_none()
    if run:
        started = run.started_at
        elapsed_ms = int((now - started).total_seconds() * 1000)
        run.run_status = "COMPLETED"
        run.completed_at = now
        run.findings_generated = findings
        run.alerts_generated = alerts
        run.actions_recommended = drafts
        run.execution_time_ms = elapsed_ms
        run.updated_at = now

    agent_stmt = select(MonitoringAgentModel).where(MonitoringAgentModel.id == agent_id)
    agent = (await session.execute(agent_stmt)).scalar_one_or_none()
    if agent:
        agent.last_run_at = now
        agent.next_run_at = now + timedelta(hours=agent.run_interval_hours)
        agent.run_count += 1
        agent.success_count += 1
        agent.status = "ACTIVE"
        agent.updated_at = now

    await session.flush()

    # Metrics
    from application.agent_monitoring.metrics import agent_counters

    runtime_ms = run.execution_time_ms if run else None
    agent_counters.record_run_completed(runtime_ms=runtime_ms)

    # Audit: run completed
    if run:
        await _log_audit_event(
            session=session,
            action="agent.run.completed",
            actor_id=agent_id,
            entity_type="MonitoringAgentRun",
            entity_id=run_id,
            detail=f"Run completed: {findings} findings, {alerts} alerts, {drafts} drafts",
            metadata={
                "findings": findings,
                "alerts": alerts,
                "drafts": drafts,
                "execution_time_ms": runtime_ms,
                "organization_id": run.organization_id,
            },
        )


_PER_ORG_FAILURE_THRESHOLD = 3  # consecutive org failures before warning


async def record_run_failed(
    run_id: str,
    agent_id: str,
    error: str,
    session,
) -> None:
    """Mark a run as failed and increment the agent's failure counter.

    F6: failure_count is per-org informational only.  The global
    MonitoringAgentModel is NEVER automatically set to FAILED from a single
    org's failures — one tenant's data issues must not disable monitoring for
    all organisations.  Admins disable agents explicitly via set_agent_enabled().
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import (
        MonitoringAgentModel,
        MonitoringAgentRunModel,
    )

    now = datetime.now(UTC)

    run_stmt = select(MonitoringAgentRunModel).where(MonitoringAgentRunModel.id == run_id)
    run = (await session.execute(run_stmt)).scalar_one_or_none()
    if run:
        started = run.started_at
        run.run_status = "FAILED"
        run.completed_at = now
        run.error_message = error[:4000]
        run.execution_time_ms = int((now - started).total_seconds() * 1000)
        run.updated_at = now

    agent_stmt = select(MonitoringAgentModel).where(MonitoringAgentModel.id == agent_id)
    agent = (await session.execute(agent_stmt)).scalar_one_or_none()
    if agent:
        agent.last_run_at = now
        interval = timedelta(hours=min(agent.run_interval_hours * 2, 48))
        agent.next_run_at = now + interval
        agent.run_count += 1
        agent.failure_count += 1
        # F6: do NOT set agent.status = "FAILED" here — that is a global action
        # that would stop monitoring for ALL organisations.  Per-org failures are
        # tracked via the run history and surfaced as a warning below.
        agent.updated_at = now

    await session.flush()

    # F6: warn if this org has accumulated consecutive failures
    org_id = run.organization_id if run else None
    if org_id:
        recent_stmt = (
            select(MonitoringAgentRunModel.run_status)
            .where(
                MonitoringAgentRunModel.agent_id == agent_id,
                MonitoringAgentRunModel.organization_id == org_id,
            )
            .order_by(MonitoringAgentRunModel.started_at.desc())
            .limit(_PER_ORG_FAILURE_THRESHOLD)
        )
        recent = list((await session.execute(recent_stmt)).scalars().all())
        if len(recent) >= _PER_ORG_FAILURE_THRESHOLD and all(s == "FAILED" for s in recent):
            logger.warning(
                "agent_org_repeated_failure",
                agent_id=agent_id,
                organization_id=org_id,
                consecutive_failures=len(recent),
                detail="Agent is repeatedly failing for this org; global agent NOT disabled.",
            )

    # Metrics
    from application.agent_monitoring.metrics import agent_counters

    runtime_ms = run.execution_time_ms if run else None
    agent_counters.record_run_failed(runtime_ms=runtime_ms)

    # Audit: run failed
    if run:
        await _log_audit_event(
            session=session,
            action="agent.run.failed",
            actor_id=agent_id,
            entity_type="MonitoringAgentRun",
            entity_id=run_id,
            detail=f"Run failed: {error[:200]}",
            metadata={
                "error": error[:500],
                "organization_id": run.organization_id,
            },
        )


async def get_agent_health_list(session) -> list[dict]:
    """Return operational health stats per agent for the dashboard.

    Computes per-agent:
      - last_successful_run (latest COMPLETED run's completed_at)
      - consecutive_failures (tail of runs where all are FAILED)
      - avg_runtime_ms (average execution_time_ms of COMPLETED runs, last 30)
      - success_rate (agent.success_count / agent.run_count)
    """
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import (
        MonitoringAgentRunModel,
    )

    agents = await list_agents(session)
    health = []

    for agent in agents:
        # Last 30 completed runs for runtime average
        completed_stmt = (
            select(MonitoringAgentRunModel.execution_time_ms)
            .where(
                MonitoringAgentRunModel.agent_id == agent.id,
                MonitoringAgentRunModel.run_status == "COMPLETED",
                MonitoringAgentRunModel.execution_time_ms.is_not(None),
            )
            .order_by(MonitoringAgentRunModel.started_at.desc())
            .limit(30)
        )
        runtimes = list((await session.execute(completed_stmt)).scalars().all())
        avg_runtime_ms = round(sum(runtimes) / len(runtimes), 1) if runtimes else None

        # Last successful run timestamp
        last_ok_stmt = (
            select(MonitoringAgentRunModel.completed_at)
            .where(
                MonitoringAgentRunModel.agent_id == agent.id,
                MonitoringAgentRunModel.run_status == "COMPLETED",
            )
            .order_by(MonitoringAgentRunModel.completed_at.desc())
            .limit(1)
        )
        last_successful_run = (await session.execute(last_ok_stmt)).scalar_one_or_none()

        # Consecutive failures: read last 10 runs and count tail of FAILEDs
        recent_stmt = (
            select(MonitoringAgentRunModel.run_status)
            .where(MonitoringAgentRunModel.agent_id == agent.id)
            .order_by(MonitoringAgentRunModel.started_at.desc())
            .limit(10)
        )
        recent = list((await session.execute(recent_stmt)).scalars().all())
        consecutive_failures = 0
        for status in recent:
            if status == "FAILED":
                consecutive_failures += 1
            else:
                break

        success_rate = None
        if agent.run_count > 0:
            success_rate = round(agent.success_count / agent.run_count, 3)

        health.append(
            {
                "agent_id": agent.id,
                "agent_type": agent.agent_type,
                "name": agent.name,
                "status": agent.status,
                "enabled": agent.enabled,
                "last_successful_run": last_successful_run,
                "consecutive_failures": consecutive_failures,
                "avg_runtime_ms": avg_runtime_ms,
                "success_rate": success_rate,
                "backlog_count": 0,  # populated by dashboard if needed
            }
        )

    return health


async def list_runs(
    agent_id: str | None = None,
    organization_id: str | None = None,
    limit: int = 50,
    session=None,
) -> list:
    from sqlalchemy import select

    from infrastructure.persistence.models.agent_monitoring import MonitoringAgentRunModel

    stmt = select(MonitoringAgentRunModel)
    if agent_id:
        stmt = stmt.where(MonitoringAgentRunModel.agent_id == agent_id)
    if organization_id:
        stmt = stmt.where(MonitoringAgentRunModel.organization_id == organization_id)
    stmt = stmt.order_by(MonitoringAgentRunModel.started_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())

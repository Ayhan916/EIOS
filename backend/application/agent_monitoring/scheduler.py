"""M36 Autonomous Agent Scheduler.

Runs as a background asyncio task inside the FastAPI lifespan.
Wakes every CHECK_INTERVAL_SECONDS, finds all due agents, and runs them
against every organization in the database.

Architecture:
  - Agents are global (not per-org). Each agent runs for each org separately.
  - Each org's run is isolated: one MonitoringAgentRun record per (agent × org).
  - Failure in one org's run does NOT abort other orgs.
  - Agents are retried with exponential backoff (failure_count drives next_run_at).

Horizontal scaling:
  - M36.2: PostgreSQL session-level advisory lock prevents duplicate execution
    across multiple app instances.  Lock key: _SCHEDULER_LOCK_KEY.
    pg_try_advisory_lock() returns false immediately if another instance holds
    the lock — the loser exits gracefully without processing.

Human approval model:
  - Scheduler may ONLY create findings, alerts, and recommendation drafts.
  - No approval, close, resolve, or delete actions.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)

_CHECK_INTERVAL_SECONDS = 3600  # wake every hour
_STARTUP_DELAY_SECONDS = 90     # give the app time to warm up
_RETENTION_INTERVAL_CYCLES = 24  # run retention cleanup every 24 cycles (~24 hours)
_SCHEDULER_LOCK_KEY = 363600     # stable PostgreSQL advisory lock key for eios agent scheduler

# Track how many scheduler cycles have run (for retention cadence)
_cycle_count = 0


async def run_agent_scheduler() -> None:
    """Main scheduler loop. Runs forever until cancelled."""
    global _cycle_count
    logger.info("agent_scheduler_started")
    await asyncio.sleep(_STARTUP_DELAY_SECONDS)

    while True:
        try:
            acquired = await _try_acquire_scheduler_lock_and_run()
            if acquired:
                _cycle_count += 1
                if _cycle_count % _RETENTION_INTERVAL_CYCLES == 0:
                    await _run_retention()
        except asyncio.CancelledError:
            logger.info("agent_scheduler_cancelled")
            raise
        except Exception as exc:
            logger.error("agent_scheduler_error", error=str(exc))

        await asyncio.sleep(_CHECK_INTERVAL_SECONDS)


async def _try_acquire_scheduler_lock_and_run() -> bool:
    """Acquire a PostgreSQL advisory lock and run due agents.

    Returns True if the lock was acquired and agents were processed.
    Returns False if another scheduler instance already holds the lock.

    Falls back to running without a lock if advisory locks are unavailable
    (e.g. non-PostgreSQL databases in tests).
    """
    from infrastructure.persistence.database import AsyncSessionFactory
    from sqlalchemy import text

    lock_session = None
    try:
        lock_session = AsyncSessionFactory()
        await lock_session.execute(text("BEGIN"))
        result = await lock_session.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": _SCHEDULER_LOCK_KEY},
        )
        locked = result.scalar_one()
        if not locked:
            logger.debug(
                "agent_scheduler_lock_not_acquired",
                detail="Another scheduler instance is running; skipping this cycle.",
            )
            return False

        await _run_due_agents()
        return True

    except Exception as exc:
        err = str(exc)
        if "pg_try_advisory_lock" in err or "advisory" in err.lower():
            # Unsupported database (e.g. SQLite in tests) — run without lock
            logger.debug("agent_scheduler_advisory_lock_unavailable", error=err)
            await _run_due_agents()
            return True
        raise
    finally:
        if lock_session is not None:
            try:
                await lock_session.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": _SCHEDULER_LOCK_KEY},
                )
                await lock_session.close()
            except Exception:
                pass


async def _run_due_agents() -> None:
    """Find due agents, collect all orgs, run each agent for each org."""
    from application.agent_monitoring.agent_service import get_due_agents
    from infrastructure.persistence.database import AsyncSessionFactory
    from infrastructure.persistence.models.organization import OrganizationModel
    from sqlalchemy import select

    async with AsyncSessionFactory() as session, session.begin():
        due_agents = await get_due_agents(session)
        if not due_agents:
            return

        org_stmt = select(OrganizationModel.id)
        org_ids = list((await session.execute(org_stmt)).scalars().all())

    if not org_ids:
        return

    logger.info(
        "agent_scheduler_cycle",
        due_agents=[a.agent_type for a in due_agents],
        org_count=len(org_ids),
    )

    for agent in due_agents:
        for org_id in org_ids:
            try:
                async with AsyncSessionFactory() as session, session.begin():
                    await _execute_agent(agent.id, agent.agent_type, org_id, session)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "agent_run_error",
                    agent_type=agent.agent_type,
                    org_id=org_id,
                    error=str(exc),
                )
                async with AsyncSessionFactory() as session, session.begin():
                    await _mark_agent_failed(agent.id, org_id, str(exc), session)


async def _execute_agent(
    agent_id: str,
    agent_type: str,
    organization_id: str,
    session,
) -> None:
    """Run a single agent for a single organization.

    F2: check_and_start_run() raises ValueError if a RUNNING record already
    exists for this (agent_id, org_id), preventing duplicate concurrent runs.

    F3: There is no record_run_failed() call in the except block here.
    The reason: _execute_agent() runs inside `async with session.begin()`.
    When _dispatch() raises and this function re-raises, the session.begin()
    context manager rolls back the entire transaction — including any
    record_run_start() and any attempted record_run_failed() write.  The
    outer _mark_agent_failed() in _run_due_agents() opens a FRESH session
    and is the sole authoritative failure recorder.
    """
    from application.agent_monitoring.agent_service import (
        check_and_start_run,
        record_run_completed,
    )

    run = await check_and_start_run(agent_id, organization_id, session)
    run_id = run.id

    # No try/except here — on exception the outer session.begin() rolls back
    # everything (including the run record), and _mark_agent_failed() records it.
    findings, alerts, drafts = await _dispatch(agent_id, agent_type, run_id, organization_id, session)
    await record_run_completed(run_id, agent_id, findings, alerts, drafts, session)
    logger.info(
        "agent_run_completed",
        agent_type=agent_type,
        org_id=organization_id,
        findings=findings,
        alerts=alerts,
        drafts=drafts,
    )


async def _dispatch(
    agent_id: str,
    agent_type: str,
    run_id: str,
    organization_id: str,
    session,
) -> tuple[int, int, int]:
    """Route to the correct monitoring agent. Returns (findings, alerts, drafts)."""
    from application.agent_monitoring import (
        compliance_drift_monitor,
        intelligence_monitor,
        regulatory_monitor,
        remediation_monitor,
        risk_monitor,
        supplier_behaviour_monitor,
    )
    from application.surveillance import (
        risk_drift_engine,
        emerging_risk_engine,
        correlation_engine,
        early_warning_engine,
        predictive_escalation_engine,
    )
    from infrastructure.persistence.models.agent_monitoring import AgentAlertModel, RecommendationDraftModel
    from sqlalchemy import func, select

    _RUN_BEFORE_FIND = (
        select(func.count())
        .select_from(AgentAlertModel)
        .where(AgentAlertModel.agent_id == agent_id)
    )

    async def _run_surveillance(agent_id, run_id, org_id, session):
        """Fan out to all M37 surveillance engines and sum signal counts."""
        total = 0
        for engine in [
            risk_drift_engine,
            emerging_risk_engine,
            correlation_engine,
            early_warning_engine,
            predictive_escalation_engine,
        ]:
            total += await engine.run(agent_id, run_id, org_id, session)
        return total

    dispatch_map = {
        "RISK_MONITOR": risk_monitor.run,
        "REGULATION_MONITOR": regulatory_monitor.run,
        "SUPPLIER_MONITOR": supplier_behaviour_monitor.run,
        "COMPLIANCE_MONITOR": compliance_drift_monitor.run,
        "REMEDIATION_MONITOR": remediation_monitor.run,
        "INTELLIGENCE_MONITOR": intelligence_monitor.run,
        "SURVEILLANCE_MONITOR": _run_surveillance,
    }

    run_fn = dispatch_map.get(agent_type)
    if run_fn is None:
        logger.warning("unknown_agent_type", agent_type=agent_type)
        return 0, 0, 0

    # Count alerts/drafts before the run to compute delta
    alerts_before = (await session.execute(
        select(func.count()).select_from(AgentAlertModel).where(AgentAlertModel.agent_id == agent_id)
    )).scalar_one()
    drafts_before = (await session.execute(
        select(func.count()).select_from(RecommendationDraftModel).where(
            RecommendationDraftModel.agent_id == agent_id
        )
    )).scalar_one()

    findings_created = await run_fn(
        agent_id=agent_id,
        agent_run_id=run_id,
        organization_id=organization_id,
        session=session,
    )

    alerts_after = (await session.execute(
        select(func.count()).select_from(AgentAlertModel).where(AgentAlertModel.agent_id == agent_id)
    )).scalar_one()
    drafts_after = (await session.execute(
        select(func.count()).select_from(RecommendationDraftModel).where(
            RecommendationDraftModel.agent_id == agent_id
        )
    )).scalar_one()

    return findings_created, alerts_after - alerts_before, drafts_after - drafts_before


async def _mark_agent_failed(
    agent_id: str,
    organization_id: str,
    error: str,
    session,
) -> None:
    """Best-effort: record a failed run if we couldn't start one."""
    from application.agent_monitoring.agent_service import record_run_failed, record_run_start

    try:
        run = await record_run_start(agent_id, organization_id, session)
        await record_run_failed(run.id, agent_id, error, session)
    except Exception as exc:
        logger.error("failed_to_record_agent_failure", agent_id=agent_id, error=str(exc))


async def trigger_agent_run(
    agent_type: str,
    organization_id: str,
    session,
) -> object:
    """Manually trigger a single agent for a single organization.

    F1: organization_id is always the calling user's org (enforced by the router).
    F2: check_and_start_run() prevents duplicate concurrent runs for the same
        (agent_type, organization_id) pair.
    """
    from application.agent_monitoring.agent_service import (
        check_and_start_run,
        get_agent_by_type,
        record_run_completed,
        record_run_failed,
    )

    agent = await get_agent_by_type(agent_type, session)
    if agent is None:
        raise ValueError(f"Unknown agent type: {agent_type!r}")
    if not agent.enabled:
        raise ValueError(f"Agent {agent_type} is disabled")

    run = await check_and_start_run(agent.id, organization_id, session)
    try:
        findings, alerts, drafts = await _dispatch(
            agent.id, agent_type, run.id, organization_id, session
        )
        await record_run_completed(run.id, agent.id, findings, alerts, drafts, session)
        return run
    except Exception as exc:
        await record_run_failed(run.id, agent.id, str(exc), session)
        raise


async def _run_retention() -> None:
    """Run retention cleanup in a separate session. Non-fatal."""
    from application.agent_monitoring.retention_service import run_retention_cleanup
    from infrastructure.persistence.database import AsyncSessionFactory

    try:
        async with AsyncSessionFactory() as session, session.begin():
            counts = await run_retention_cleanup(session)
        logger.info("agent_retention_completed", **counts)
    except Exception as exc:
        logger.error("agent_retention_failed", error=str(exc))

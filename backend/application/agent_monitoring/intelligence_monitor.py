"""M36 External Intelligence Agent.

Monitors:
  - Suppliers in countries with deteriorating risk scores (country risk < 40)
  - Sanctions exposure changes (sanctions_status = 'confirmed' or 'suspected')
  - Corruption index below threshold
  - Governance score decline

Integrates with M34 (CountryRiskProfileModel, SupplierEnrichmentModel).
No destructive actions. All outputs are AgentFindings.

F4 (M36.1): All external data is validated for freshness and quarantine status
before use.  Stale or quarantined data silently skips — never generates findings.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

from application.agent_monitoring.finding_service import create_finding

logger = structlog.get_logger(__name__)

_COUNTRY_RISK_HIGH = 60.0         # overall_risk_score above this = HIGH
_COUNTRY_RISK_CRITICAL = 80.0     # overall_risk_score above this = CRITICAL
_GOVERNANCE_LOW = 30.0            # governance_score below this = concern
_CORRUPTION_HIGH = 70.0           # corruption_score above this = HIGH risk
_DATA_FRESHNESS_DAYS = 30         # F4: max age for external dataset to be trusted


async def run(agent_id: str, agent_run_id: str, organization_id: str, session) -> int:
    """Run external intelligence monitor for one organization. Returns findings created."""
    from infrastructure.persistence.models.supplier import SupplierModel
    from infrastructure.persistence.models.external_intelligence import (
        CountryRiskProfileModel,
        ExternalDatasetModel,
        SupplierEnrichmentModel,
    )
    from sqlalchemy import select

    findings_created = 0
    now = datetime.now(UTC)
    freshness_cutoff = now - timedelta(days=_DATA_FRESHNESS_DAYS)

    # F4: Identify valid (active + fresh) external dataset IDs.
    # Quarantined or stale datasets must never be used to generate findings.
    valid_dataset_stmt = select(ExternalDatasetModel.id).where(
        ExternalDatasetModel.dataset_status == "active",
        ExternalDatasetModel.imported_at >= freshness_cutoff,
    )
    valid_dataset_ids = set((await session.execute(valid_dataset_stmt)).scalars().all())

    if not valid_dataset_ids:
        logger.warning(
            "intelligence_monitor_no_valid_datasets",
            organization_id=organization_id,
            freshness_cutoff=str(freshness_cutoff),
            detail="No active/fresh external datasets found — skipping intelligence run",
        )
        return 0

    # Load active suppliers
    suppliers_stmt = select(SupplierModel).where(
        SupplierModel.organization_id == organization_id,
        SupplierModel.supplier_status == "Active",
    )
    suppliers = list((await session.execute(suppliers_stmt)).scalars().all())

    # F4: Country risk profiles from valid datasets only
    country_risk_stmt = select(CountryRiskProfileModel).where(
        CountryRiskProfileModel.dataset_id.in_(valid_dataset_ids)
    )
    country_profiles = list((await session.execute(country_risk_stmt)).scalars().all())
    country_risk_by_code = {p.country_code: p for p in country_profiles}
    country_risk_by_name = {p.country_name.lower(): p for p in country_profiles}

    for supplier in suppliers:
        # L4: null-guard supplier.country before calling .strip()
        country = (supplier.country or "").strip()
        if not country:
            logger.debug(
                "intelligence_monitor_no_country",
                supplier_id=supplier.id,
                supplier_name=supplier.name,
            )
            continue

        source_data_base = {
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "country": country,
        }

        # Look up country risk profile
        profile = country_risk_by_code.get(country) or country_risk_by_name.get(country.lower())
        if profile:
            source_data = {
                **source_data_base,
                "overall_risk_score": profile.overall_risk_score,
                "risk_level": profile.risk_level,
                "governance_score": profile.governance_score,
                "corruption_score": profile.corruption_score,
                "sanctions_status": profile.sanctions_status,
            }

            # Rule 1: Sanctions exposure
            if profile.sanctions_status in ("confirmed", "suspected"):
                severity = "CRITICAL" if profile.sanctions_status == "confirmed" else "HIGH"
                finding = await create_finding(
                    organization_id=organization_id,
                    agent_id=agent_id,
                    category="sanctions_exposure",
                    severity=severity,
                    title=f"Sanctions exposure: {supplier.name} ({country})",
                    description=(
                        f"Supplier {supplier.name} is located in {country}, "
                        f"which has sanctions status: {profile.sanctions_status}. "
                        "Immediate review and legal assessment required."
                    ),
                    evidence=f"country={country}, sanctions_status={profile.sanctions_status}",
                    rule_triggered=f"sanctions_status in ['confirmed', 'suspected']",
                    source_data={"sanctions_exposure": True, **source_data},
                    confidence_score=0.95,
                    supplier_id=supplier.id,
                    agent_run_id=agent_run_id,
                    session=session,
                )
                await _maybe_escalate(finding, organization_id, session)
                findings_created += 1
                continue  # don't double-report — sanctions is highest priority

            # Rule 2: High country risk score
            if profile.overall_risk_score >= _COUNTRY_RISK_CRITICAL:
                finding = await create_finding(
                    organization_id=organization_id,
                    agent_id=agent_id,
                    category="country_risk",
                    severity="CRITICAL",
                    title=f"Critical country risk: {supplier.name} in {country}",
                    description=(
                        f"Supplier {supplier.name} operates in {country} "
                        f"(country risk score: {profile.overall_risk_score:.1f}, "
                        f"level: {profile.risk_level}). "
                        "Consider enhanced due diligence or supply chain diversification."
                    ),
                    evidence=(
                        f"country_risk={profile.overall_risk_score:.1f}, "
                        f"level={profile.risk_level}"
                    ),
                    rule_triggered=f"overall_risk_score >= {_COUNTRY_RISK_CRITICAL}",
                    source_data=source_data,
                    confidence_score=0.9,
                    supplier_id=supplier.id,
                    agent_run_id=agent_run_id,
                    session=session,
                )
                await _maybe_escalate(finding, organization_id, session)
                findings_created += 1

            elif profile.overall_risk_score >= _COUNTRY_RISK_HIGH:
                finding = await create_finding(
                    organization_id=organization_id,
                    agent_id=agent_id,
                    category="country_risk",
                    severity="HIGH",
                    title=f"High country risk: {supplier.name} in {country}",
                    description=(
                        f"Supplier {supplier.name} operates in {country} "
                        f"(country risk score: {profile.overall_risk_score:.1f}). "
                        "Enhanced monitoring recommended."
                    ),
                    evidence=f"country_risk={profile.overall_risk_score:.1f}",
                    rule_triggered=f"overall_risk_score >= {_COUNTRY_RISK_HIGH}",
                    source_data=source_data,
                    confidence_score=0.85,
                    supplier_id=supplier.id,
                    agent_run_id=agent_run_id,
                    session=session,
                )
                await _maybe_escalate(finding, organization_id, session)
                findings_created += 1

            # Rule 3: Corruption concern
            if profile.corruption_score >= _CORRUPTION_HIGH:
                finding = await create_finding(
                    organization_id=organization_id,
                    agent_id=agent_id,
                    category="corruption_risk",
                    severity="HIGH",
                    title=f"High corruption risk: {supplier.name} in {country}",
                    description=(
                        f"Supplier {supplier.name}'s country ({country}) has a high "
                        f"corruption score of {profile.corruption_score:.1f}. "
                        "Anti-bribery controls and enhanced due diligence recommended."
                    ),
                    evidence=f"corruption_score={profile.corruption_score:.1f}",
                    rule_triggered=f"corruption_score >= {_CORRUPTION_HIGH}",
                    source_data=source_data,
                    confidence_score=0.8,
                    supplier_id=supplier.id,
                    agent_run_id=agent_run_id,
                    session=session,
                )
                await _maybe_escalate(finding, organization_id, session)
                findings_created += 1

        # Rule 4: Supplier enrichment — check direct sanctions flag (F4: fresh only)
        enrich_stmt = (
            select(SupplierEnrichmentModel)
            .where(
                SupplierEnrichmentModel.supplier_id == supplier.id,
                SupplierEnrichmentModel.enriched_at >= freshness_cutoff,
            )
            .order_by(SupplierEnrichmentModel.enriched_at.desc())
            .limit(1)
        )
        enrichment = (await session.execute(enrich_stmt)).scalar_one_or_none()
        if enrichment is None:
            logger.debug(
                "intelligence_monitor_stale_enrichment",
                supplier_id=supplier.id,
                detail=f"No enrichment data fresher than {_DATA_FRESHNESS_DAYS} days — skipping",
            )
        if enrichment and enrichment.sanctions_flag:
            finding = await create_finding(
                organization_id=organization_id,
                agent_id=agent_id,
                category="direct_sanctions",
                severity="CRITICAL",
                title=f"Direct sanctions flag: {supplier.name}",
                description=(
                    f"Supplier {supplier.name} has a direct sanctions flag in enrichment data. "
                    "Immediate legal review required before continuing business relationship."
                ),
                evidence=f"sanctions_flag=True, enrichment_id={enrichment.id}",
                rule_triggered="supplier_enrichment.sanctions_flag = True",
                source_data={
                    **source_data_base,
                    "sanctions_exposure": True,
                    "enrichment_id": enrichment.id,
                },
                confidence_score=0.95,
                supplier_id=supplier.id,
                agent_run_id=agent_run_id,
                session=session,
            )
            await _maybe_escalate(finding, organization_id, session)
            findings_created += 1

    logger.info(
        "intelligence_monitor_completed",
        organization_id=organization_id,
        suppliers_checked=len(suppliers),
        findings_created=findings_created,
    )
    return findings_created


async def _maybe_escalate(finding, organization_id: str, session) -> None:
    try:
        from application.agent_monitoring.alert_service import evaluate_finding

        await evaluate_finding(finding, organization_id, session, agent_type="INTELLIGENCE_MONITOR")
    except Exception as exc:
        logger.warning("intelligence_monitor_escalation_failed", error=str(exc))

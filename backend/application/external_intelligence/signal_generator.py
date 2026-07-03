"""Auto signal generation for newly added suppliers — M34.3.

Called as a background task when a supplier is created or updated.
Reads the existing CountryRiskProfile for the supplier's country and
emits ExternalRiskSignal records based on risk score thresholds.

Signal deduplication: one active signal per (supplier_id, signal_type, source_name).
If an identical active signal already exists it is left unchanged.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import EntityStatus, ExternalSourceName, RiskSignalType, SignalSeverity
from domain.external_intelligence import ExternalRiskSignal
from .event_attribution import derive_esg_category, derive_protected_right

logger = structlog.get_logger(__name__)

# (score_field, signal_type, source_name, thresholds: list[(min_score, severity, description_tpl)])
_SIGNAL_RULES: list[tuple[str, str, str, list[tuple[float, str, str]]]] = [
    (
        "corruption_score",
        RiskSignalType.CORRUPTION.value,
        ExternalSourceName.TRANSPARENCY_INTERNATIONAL.value,
        [
            (70.0, SignalSeverity.CRITICAL.value, "Kritisch hohes Korruptionsrisiko in {country} (Score: {score:.0f}/100)"),
            (50.0, SignalSeverity.HIGH.value,     "Hohes Korruptionsrisiko in {country} (Score: {score:.0f}/100)"),
            (35.0, SignalSeverity.MEDIUM.value,   "Erhöhtes Korruptionsrisiko in {country} (Score: {score:.0f}/100)"),
        ],
    ),
    (
        "governance_score",
        RiskSignalType.GOVERNANCE.value,
        ExternalSourceName.WORLD_BANK.value,
        [
            (70.0, SignalSeverity.HIGH.value,     "Schwache Regierungsführung in {country} (Score: {score:.0f}/100)"),
            (50.0, SignalSeverity.MEDIUM.value,   "Mäßige Governance-Qualität in {country} (Score: {score:.0f}/100)"),
        ],
    ),
    (
        "labour_rights_score",
        RiskSignalType.LABOUR_RIGHTS.value,
        ExternalSourceName.ILO.value,
        [
            (70.0, SignalSeverity.HIGH.value,     "Erhebliche Verletzungen der Arbeitsrechte in {country} (Score: {score:.0f}/100)"),
            (50.0, SignalSeverity.MEDIUM.value,   "Arbeitsrechtsrisiko in {country} (Score: {score:.0f}/100)"),
        ],
    ),
    (
        "human_rights_score",
        RiskSignalType.LABOUR_RIGHTS.value,
        ExternalSourceName.UNICEF.value,
        [
            (70.0, SignalSeverity.HIGH.value,     "Hohes Menschenrechtsrisiko in {country} (Score: {score:.0f}/100)"),
            (50.0, SignalSeverity.MEDIUM.value,   "Erhöhtes Menschenrechtsrisiko in {country} (Score: {score:.0f}/100)"),
        ],
    ),
    (
        "environmental_risk_score",
        RiskSignalType.ENVIRONMENTAL.value,
        ExternalSourceName.WORLD_BANK.value,
        [
            (70.0, SignalSeverity.HIGH.value,     "Hohes Umweltrisiko in {country} (Score: {score:.0f}/100)"),
            (50.0, SignalSeverity.MEDIUM.value,   "Umweltrisiko in {country} (Score: {score:.0f}/100)"),
        ],
    ),
]

_SANCTIONS_SOURCE_MAP = {
    "comprehensive": (SignalSeverity.CRITICAL.value, "Umfassendes Sanktionsregime gegen {country} — Lieferant betroffen"),
    "partial":       (SignalSeverity.HIGH.value,     "Teilsanktionen gegen {country} — erhöhtes Compliance-Risiko"),
}


async def generate_signals_for_supplier(
    supplier_id: str,
    supplier_name: str,
    country_code: str,
    organization_id: str,
    session: AsyncSession,
) -> int:
    """Generate risk signals for a supplier based on its country's risk profile.

    Returns the number of new signals created.
    """
    if not country_code:
        return 0

    from application.external_intelligence.country_risk_service import get_country_risk
    from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel

    profile = await get_country_risk(country_code.upper(), session)
    if profile is None:
        logger.debug("no_country_risk_profile", country=country_code, supplier_id=supplier_id)
        return 0

    country_name = profile.country_name or country_code
    now = datetime.now(UTC)
    created = 0

    async def _upsert(signal_type: str, source_name: str, severity: str, description: str) -> None:
        nonlocal created
        # Dedup: skip if identical active signal already exists
        stmt = select(ExternalRiskSignalModel).where(
            ExternalRiskSignalModel.supplier_id == supplier_id,
            ExternalRiskSignalModel.signal_type == signal_type,
            ExternalRiskSignalModel.source_name == source_name,
            ExternalRiskSignalModel.organization_id == organization_id,
            ExternalRiskSignalModel.is_active.is_(True),
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return

        model = ExternalRiskSignalModel(
            id=str(uuid.uuid4()),
            status=EntityStatus.ACTIVE.value,
            version=1,
            owner="",
            created_by="system",
            updated_by="system",
            created_at=now,
            updated_at=now,
            signal_type=signal_type,
            severity=severity,
            description=description,
            source_name=source_name,
            source_version="auto",
            observed_at=now,
            dataset_id=None,
            country_code=country_code.upper(),
            sector_code="",
            supplier_id=supplier_id,
            organization_id=organization_id,
            is_active=True,
            esg_category=derive_esg_category(signal_type),
            protected_right=derive_protected_right(signal_type),
            frequency=0,
        )
        session.add(model)
        created += 1

    # Score-based signals
    for score_field, signal_type, source_name, thresholds in _SIGNAL_RULES:
        score = getattr(profile, score_field, None)
        if score is None:
            continue
        for min_score, severity, desc_tpl in thresholds:
            if score >= min_score:
                desc = desc_tpl.format(country=country_name, score=score, supplier=supplier_name)
                await _upsert(signal_type, source_name, severity, desc)
                break  # only highest threshold per rule

    # Sanctions signal
    sanctions = getattr(profile, "sanctions_status", "") or ""
    if sanctions in _SANCTIONS_SOURCE_MAP:
        severity, desc_tpl = _SANCTIONS_SOURCE_MAP[sanctions]
        desc = desc_tpl.format(country=country_name, supplier=supplier_name)
        source = ExternalSourceName.UN_SANCTIONS.value
        await _upsert(RiskSignalType.SANCTIONS.value, source, severity, desc)

    if created:
        await session.flush()
        logger.info(
            "supplier_signals_generated",
            supplier_id=supplier_id,
            country=country_code,
            count=created,
        )
    return created


async def auto_enrich_supplier_background(
    supplier_id: str,
    supplier_name: str,
    country_code: str,
    nace_code: str,
    organization_id: str,
) -> None:
    """Background task: enrich a supplier and generate signals after creation."""
    from infrastructure.persistence.database import AsyncSessionFactory

    try:
        async with AsyncSessionFactory() as session, session.begin():
            # 1. Check if country risk profile exists — if not, run collector first
            from application.external_intelligence.country_risk_service import get_country_risk
            profile = await get_country_risk(country_code.upper(), session)
            if profile is None:
                logger.info(
                    "auto_enrich_no_profile_running_collector",
                    supplier_id=supplier_id,
                    country=country_code,
                )
                try:
                    from application.intelligence_engine.collector_orchestrator import run_collection_for_org
                    await run_collection_for_org(org_id=organization_id, session=session)
                    await session.flush()
                except Exception as collect_exc:
                    logger.warning("auto_enrich_collector_failed", error=str(collect_exc))

        # 2. Generate country-based signals (new session after collector ran)
        async with AsyncSessionFactory() as session, session.begin():
            await generate_signals_for_supplier(
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                country_code=country_code,
                organization_id=organization_id,
                session=session,
            )

            # 3. Run full enrichment (scores, benchmark, combined risk)
            from application.external_intelligence.enrichment_service import enrich_supplier
            await enrich_supplier(
                supplier_id=supplier_id,
                organization_id=organization_id,
                country_code=country_code,
                sector_id="",
                nace_code=nace_code or "",
                internal_esg_score=50.0,
                session=session,
            )

    except Exception as exc:
        logger.error(
            "auto_enrich_supplier_failed",
            supplier_id=supplier_id,
            error=str(exc),
        )

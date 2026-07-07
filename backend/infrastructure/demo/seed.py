"""Demo mode seed — idempotent creation of isolated demo org + data."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from domain.assessment import Assessment
from domain.enums import (
    ConfidenceLevel,
    EntityStatus,
    ReviewStatus,
    RiskLevel,
    SupplierStatus,
    SupplierTier,
    UserRole,
)
from domain.finding import Finding
from domain.organization import Organization
from domain.recommendation import Recommendation
from domain.risk import Risk
from domain.supplier import Supplier
from domain.user import User
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLFindingRepository,
    SQLOrganizationRepository,
    SQLRecommendationRepository,
    SQLRiskRepository,
    SQLUserRepository,
)
from infrastructure.persistence.repositories.supplier import SQLSupplierRepository
from shared.security import hash_password

DEMO_ORG_ID = "org-demo-eios-2024"
DEMO_USER_EMAIL = "demo@eios.internal"
DEMO_USER_PASSWORD = "DemoEIOS2024!"


async def is_demo_seeded(session: AsyncSession) -> bool:
    user_repo = SQLUserRepository(session)
    return await user_repo.get_by_email(DEMO_USER_EMAIL) is not None


async def ensure_demo_data(session: AsyncSession) -> User:
    """Create demo org + data if not present. Returns demo user."""
    user_repo = SQLUserRepository(session)
    existing = await user_repo.get_by_email(DEMO_USER_EMAIL)
    if existing is not None:
        return existing
    return await _seed(session)


async def reset_demo_data(session: AsyncSession) -> User:
    """Wipe all demo-org rows and re-seed from scratch."""
    await _wipe_demo_data(session)
    return await _seed(session)


async def _wipe_demo_data(session: AsyncSession) -> None:
    from sqlalchemy import text

    # recommendations and findings join via assessments; risks join via created_by (demo user)
    await session.execute(
        text(
            "DELETE FROM recommendations WHERE assessment_id IN "  # noqa: S608
            "(SELECT id FROM assessments WHERE organization_id = :oid)"
        ),
        {"oid": DEMO_ORG_ID},
    )
    await session.execute(
        text(
            "DELETE FROM findings WHERE assessment_id IN "  # noqa: S608
            "(SELECT id FROM assessments WHERE organization_id = :oid)"
        ),
        {"oid": DEMO_ORG_ID},
    )
    await session.execute(
        text(
            "DELETE FROM risks WHERE created_by IN "  # noqa: S608
            "(SELECT id FROM users WHERE organization_id = :oid)"
        ),
        {"oid": DEMO_ORG_ID},
    )
    for table in ("assessments", "suppliers", "users", "organizations"):
        col = "id" if table == "organizations" else "organization_id"
        await session.execute(
            text(f"DELETE FROM {table} WHERE {col} = :oid"),  # noqa: S608
            {"oid": DEMO_ORG_ID},
        )
    await session.flush()


async def _seed(session: AsyncSession) -> User:
    org_repo = SQLOrganizationRepository(session)
    user_repo = SQLUserRepository(session)
    supplier_repo = SQLSupplierRepository(session)
    assess_repo = SQLAssessmentRepository(session)
    finding_repo = SQLFindingRepository(session)
    risk_repo = SQLRiskRepository(session)
    rec_repo = SQLRecommendationRepository(session)

    # ── Organisation ──────────────────────────────────────────────────────────
    org = Organization(
        id=DEMO_ORG_ID,
        name="EIOS Demo GmbH",
        status=EntityStatus.ACTIVE,
    )
    await org_repo.save(org)

    # ── Demo user (admin) ─────────────────────────────────────────────────────
    demo_user = User(
        email=DEMO_USER_EMAIL,
        display_name="Demo Admin",
        role=UserRole.ADMIN.value,
        organization_id=DEMO_ORG_ID,
        is_active=True,
        status=EntityStatus.ACTIVE,
        password_hash=hash_password(DEMO_USER_PASSWORD),
    )
    saved_user = await user_repo.save(demo_user)
    actor = saved_user.id

    # ── Lieferanten ───────────────────────────────────────────────────────────
    suppliers_raw = [
        ("Eco Fashion GmbH", "DE", "Textil & Bekleidung", "C14", SupplierTier.TIER_1),
        ("GreenTech Components", "CN", "Elektronik", "C26", SupplierTier.TIER_2),
        ("BioPackaging Solutions", "NL", "Verpackung", "C17", SupplierTier.TIER_1),
        ("Atlas Mining Co.", "ZA", "Bergbau", "B07", SupplierTier.TIER_3),
        ("Nordic Logistics AB", "SE", "Transport & Logistik", "H49", SupplierTier.TIER_2),
    ]
    saved_suppliers: list[Supplier] = []
    for name, country, industry, nace, tier in suppliers_raw:
        s = Supplier(
            organization_id=DEMO_ORG_ID,
            name=name,
            country=country,
            industry=industry,
            nace_code=nace,
            supplier_tier=tier,
            supplier_status=SupplierStatus.ACTIVE,
            status=EntityStatus.ACTIVE,
            created_by=actor,
        )
        saved_suppliers.append(await supplier_repo.save(s))

    eco_fashion = saved_suppliers[0]
    atlas_mining = saved_suppliers[3]

    # ── Assessments ───────────────────────────────────────────────────────────
    a1 = Assessment(
        title="Annual ESG Due Diligence 2024",
        description="Jahres-ESG-Prüfung für alle Tier-1-Lieferanten gemäß CSDDD.",
        assessment_type="due_diligence",
        scope="Tier 1 Lieferanten",
        confidence=ConfidenceLevel.HIGH,
        review_status=ReviewStatus.APPROVED,
        status=EntityStatus.ACTIVE,
        organization_id=DEMO_ORG_ID,
        supplier_id=eco_fashion.id,
        created_by=actor,
    )
    saved_a1 = await assess_repo.save(a1)

    a2 = Assessment(
        title="CSDDD-Compliance-Check Q1 2025",
        description="Überprüfung der Lieferkettensorgfaltspflichten nach CSDDD Art. 5–7.",
        assessment_type="quick_scan",
        scope="Tier 2 & 3 Lieferanten",
        confidence=ConfidenceLevel.MEDIUM,
        review_status=ReviewStatus.DRAFT,
        status=EntityStatus.ACTIVE,
        organization_id=DEMO_ORG_ID,
        supplier_id=atlas_mining.id,
        created_by=actor,
    )
    saved_a2 = await assess_repo.save(a2)

    # ── Findings ──────────────────────────────────────────────────────────────
    findings_raw = [
        (
            "Kinderarbeit in Tier-3-Lieferkette",
            "Hinweise auf Beschäftigung Minderjähriger in Zulieferbetrieben von Atlas Mining Co.",
            "Social",
            saved_a1.id,
        ),
        (
            "CO₂-Emissionen überschreiten Zielwert um 23 %",
            "Scope-3-Emissionen liegen deutlich über dem Science-Based-Target-Pfad.",
            "Environmental",
            saved_a1.id,
        ),
        (
            "Fehlende Umweltzertifizierungen",
            "ISO 14001-Zertifizierung bei 3 von 5 Lieferanten abgelaufen.",
            "Environmental",
            saved_a1.id,
        ),
        (
            "Lohnverstöße bei Atlas Mining Co.",
            "Berichte über Löhne unterhalb des gesetzlichen Mindestlohns.",
            "Social",
            saved_a2.id,
        ),
        (
            "Wasserverbrauch überschreitet Grenzwert",
            "Wasserentnahme überschreitet lokale Regulierungsobergrenzen.",
            "Environmental",
            saved_a2.id,
        ),
    ]
    for title, desc, category, aid in findings_raw:
        f = Finding(
            title=title,
            description=desc,
            category=category,
            assessment_id=aid,
            status=EntityStatus.ACTIVE,
            created_by=actor,
        )
        await finding_repo.save(f)

    # ── Risks ─────────────────────────────────────────────────────────────────
    risks_raw = [
        (
            "Lieferkettenunterbrechung",
            "Ausfall eines Tier-2-Lieferanten könnte Produktion für 6–8 Wochen stoppen.",
            RiskLevel.HIGH,
            0.6,
            0.8,
        ),
        (
            "Regulatorische Non-Compliance (CSDDD)",
            "Unzureichende Due-Diligence-Dokumentation für bevorstehende Prüfung.",
            RiskLevel.CRITICAL,
            0.4,
            0.95,
        ),
        (
            "Reputationsrisiko durch Lieferanten-Audit",
            "Negative Medienberichterstattung bei Audit-Veröffentlichung.",
            RiskLevel.MEDIUM,
            0.3,
            0.7,
        ),
        (
            "Datenschutzverletzung",
            "Lieferanten-Portal ohne ausreichende Datenverschlüsselung.",
            RiskLevel.MEDIUM,
            0.25,
            0.65,
        ),
    ]
    for title, desc, level, prob, impact in risks_raw:
        r = Risk(
            title=title,
            description=desc,
            risk_level=level,
            probability=prob,
            impact=impact,
            status=EntityStatus.ACTIVE,
            created_by=actor,
        )
        await risk_repo.save(r)

    # ── Recommendations ───────────────────────────────────────────────────────
    recs_raw = [
        (
            "Lieferanten-Code of Conduct einführen",
            "Verbindlichen Verhaltenskodex für alle Tier-1-Lieferanten mit Unterschriftspflicht.",
            saved_a1.id,
        ),
        (
            "Vor-Ort-Audit — Atlas Mining Co.",
            "Unabhängiges Audit zur Überprüfung der Arbeitsbedingungen bis Q2 2025.",
            saved_a2.id,
        ),
        (
            "Carbon-Offset-Programm für Scope-3-Emissionen",
            "Zertifizierte Kompensationsprojekte zur Erreichung des 1,5°C-Pfads.",
            saved_a1.id,
        ),
    ]
    for title, desc, aid in recs_raw:
        rec = Recommendation(
            title=title,
            description=desc,
            assessment_id=aid,
            status=EntityStatus.ACTIVE,
            created_by=actor,
        )
        await rec_repo.save(rec)

    await session.flush()
    return saved_user

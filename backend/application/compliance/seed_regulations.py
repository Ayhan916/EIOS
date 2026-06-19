"""Idempotent seed loader for regulatory frameworks.

Called once at startup. Inserts Regulation and RegulationRequirement records
from the static framework catalog if they don't already exist (checked by code).
Safe to call on every restart — existing records are never overwritten.
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from application.compliance.frameworks import (
    CSRD,
    CSDDD,
    EU_TAXONOMY,
    ESRS,
    GRI,
    ISSB,
    LKSG,
    TCFD,
    FrameworkArticle,
)
from domain.enums import EntityStatus
from domain.regulation import Regulation, RegulationRequirement
from infrastructure.persistence.repositories.regulatory import (
    SQLRegulationRepository,
    SQLRegulationRequirementRepository,
)

log = structlog.get_logger(__name__)

# Maps framework code → (name, jurisdiction, description)
_FRAMEWORK_META: dict[str, tuple[str, str, str]] = {
    "CSRD": (
        "Corporate Sustainability Reporting Directive",
        "EU",
        "EU directive requiring large companies to report on sustainability matters.",
    ),
    "CSDDD": (
        "Corporate Sustainability Due Diligence Directive",
        "EU",
        "EU directive requiring companies to conduct human rights and environmental due diligence.",
    ),
    "ESRS": (
        "European Sustainability Reporting Standards",
        "EU",
        "Technical reporting standards under CSRD defining disclosure requirements.",
    ),
    "LkSG": (
        "Lieferkettensorgfaltspflichtengesetz (Supply Chain Due Diligence Act)",
        "DE",
        "German law requiring companies to conduct due diligence across their supply chains.",
    ),
    "GRI": (
        "Global Reporting Initiative Standards",
        "Global",
        "Voluntary international standards for sustainability reporting.",
    ),
    "EU_TAXONOMY": (
        "EU Taxonomy Regulation",
        "EU",
        "EU classification system for environmentally sustainable economic activities.",
    ),
    "ISSB": (
        "IFRS Sustainability Disclosure Standards (S1 & S2)",
        "Global",
        "International baseline for sustainability-related financial disclosures.",
    ),
    "TCFD": (
        "Task Force on Climate-related Financial Disclosures",
        "Global",
        "Framework for climate-related risk and opportunity disclosures to investors.",
    ),
}

_PILLAR_MAP = {
    "Environmental": "E",
    "Social": "S",
    "Governance": "G",
}

_ALL_FRAMEWORK_ARTICLES: list[tuple[str, list[FrameworkArticle]]] = [
    ("CSRD", CSRD),
    ("CSDDD", CSDDD),
    ("ESRS", ESRS),
    ("LkSG", LKSG),
    ("GRI", GRI),
    ("EU_TAXONOMY", EU_TAXONOMY),
    ("ISSB", ISSB),
    ("TCFD", TCFD),
]

_OBLIGATION_SEVERITY = {
    "mandatory": "High",
    "recommended": "Medium",
}


def _bump_version(current: str) -> str:
    """Increment minor version: '1.0' → '1.1' → '1.2'."""
    parts = current.split(".")
    if len(parts) == 2:
        major, minor = parts
        try:
            return f"{major}.{int(minor) + 1}"
        except ValueError:
            pass
    return current + ".1"


async def seed_regulatory_data(session: AsyncSession) -> None:
    """Insert regulations and requirements that don't already exist.

    When new requirements are detected for an existing regulation (i.e., a
    catalog update), the regulation's reg_version is bumped so historical gap
    records remain traceable to the framework version that produced them.
    """
    reg_repo = SQLRegulationRepository(session)
    req_repo = SQLRegulationRequirementRepository(session)

    inserted_regs = 0
    inserted_reqs = 0
    bumped_versions = 0

    for fw_code, articles in _ALL_FRAMEWORK_ARTICLES:
        # Upsert regulation
        existing_reg = await reg_repo.get_by_code(fw_code)
        if existing_reg is None:
            meta = _FRAMEWORK_META.get(fw_code, (fw_code, "Global", ""))
            reg = Regulation(
                code=fw_code,
                name=meta[0],
                jurisdiction=meta[1],
                reg_version="1.0",
                reg_status="active",
                description=meta[2],
                status=EntityStatus.ACTIVE,
            )
            existing_reg = await reg_repo.save(reg)
            inserted_regs += 1

        # Upsert requirements; track whether any new ones were inserted
        new_reqs_for_reg = 0
        for article in articles:
            existing_req = await req_repo.get_by_code(article.code)
            if existing_req is None:
                first_cat = article.esg_categories[0] if article.esg_categories else "Governance"
                pillar = _PILLAR_MAP.get(first_cat, "G")
                req = RegulationRequirement(
                    regulation_id=existing_reg.id,
                    code=article.code,
                    reference=article.article,
                    title=article.title,
                    description="",
                    category=first_cat,
                    pillar=pillar,
                    severity=_OBLIGATION_SEVERITY.get(article.obligation_type, "Medium"),
                    obligation_type=article.obligation_type,
                    keywords=list(article.keywords),
                    status=EntityStatus.ACTIVE,
                )
                await req_repo.save(req)
                inserted_reqs += 1
                new_reqs_for_reg += 1

        # If new requirements were added to an already-existing regulation,
        # bump its reg_version so gap records can distinguish old from new.
        if new_reqs_for_reg > 0 and inserted_regs == 0:
            bumped = Regulation(
                id=existing_reg.id,
                code=existing_reg.code,
                name=existing_reg.name,
                jurisdiction=existing_reg.jurisdiction,
                reg_version=_bump_version(existing_reg.reg_version),
                reg_status=existing_reg.reg_status,
                description=existing_reg.description,
                status=existing_reg.status,
                version=existing_reg.version,
                owner=existing_reg.owner,
                created_by=existing_reg.created_by,
                updated_by=existing_reg.updated_by,
                created_at=existing_reg.created_at,
                updated_at=existing_reg.updated_at,
            )
            await reg_repo.save(bumped)
            bumped_versions += 1

    if inserted_regs or inserted_reqs or bumped_versions:
        log.info(
            "regulatory_seed_complete",
            regulations_inserted=inserted_regs,
            requirements_inserted=inserted_reqs,
            versions_bumped=bumped_versions,
        )

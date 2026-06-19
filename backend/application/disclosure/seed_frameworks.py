"""M32 Disclosure Framework Seed.

Seeds the five initial sustainability reporting frameworks and their
disclosure requirements. Idempotent — only inserts records that are absent.

Frameworks seeded:
  CSRD  — Corporate Sustainability Reporting Directive
  ESRS  — European Sustainability Reporting Standards
  ISSB  — ISSB Sustainability Disclosure Standards
  GRI   — Global Reporting Initiative Standards
  TCFD  — Task Force on Climate-related Financial Disclosures
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from domain.disclosure import DisclosureFramework, DisclosureRequirement
from domain.enums import EntityStatus
from infrastructure.persistence.repositories.disclosure import (
    SQLDisclosureFrameworkRepository,
    SQLDisclosureRequirementRepository,
)


_FRAMEWORKS: list[dict] = [
    {
        "code": "CSRD",
        "name": "Corporate Sustainability Reporting Directive",
        "version": "1.0",
        "jurisdiction": "EU",
        "effective_date": date(2024, 1, 1),
        "description": "EU directive requiring large companies to report on sustainability matters.",
        "requirements": [
            ("CSRD-Gen-1", "General Principles", "Principles for sustainability reporting"),
            ("CSRD-E-1", "Environmental Matters", "Disclosures on environmental impacts"),
            ("CSRD-S-1", "Social Matters", "Disclosures on workforce and social topics"),
            ("CSRD-G-1", "Governance Matters", "Corporate governance disclosures"),
            ("CSRD-Art19a", "Sustainability Statement", "Consolidated sustainability statement under Art. 19a"),
            ("CSRD-Art29a", "Group Sustainability Statement", "Group-level sustainability statement under Art. 29a"),
            ("CSRD-Due-1", "Due Diligence Process", "Description of due diligence process"),
            ("CSRD-Risk-1", "Principal Risks", "Principal risks related to sustainability matters"),
        ],
    },
    {
        "code": "ESRS",
        "name": "European Sustainability Reporting Standards",
        "version": "1.0",
        "jurisdiction": "EU",
        "effective_date": date(2024, 1, 1),
        "description": "EFRAG standards specifying disclosure requirements under CSRD.",
        "requirements": [
            ("ESRS-E1", "Climate Change", "Disclosures on climate change mitigation and adaptation"),
            ("ESRS-E2", "Pollution", "Disclosures on air, water and soil pollution"),
            ("ESRS-E3", "Water & Marine Resources", "Disclosures on water use and marine resources"),
            ("ESRS-E4", "Biodiversity & Ecosystems", "Disclosures on biodiversity and ecosystem services"),
            ("ESRS-E5", "Circular Economy", "Disclosures on resource use and circular economy"),
            ("ESRS-S1", "Own Workforce", "Disclosures on own employees and workers"),
            ("ESRS-S2", "Workers in Value Chain", "Disclosures on workers in the value chain"),
            ("ESRS-S3", "Affected Communities", "Disclosures on affected communities"),
            ("ESRS-S4", "Consumers & End-users", "Disclosures on consumers and end-users"),
            ("ESRS-G1", "Business Conduct", "Disclosures on business conduct and ethics"),
        ],
    },
    {
        "code": "ISSB",
        "name": "ISSB Sustainability Disclosure Standards",
        "version": "1.0",
        "jurisdiction": "Global",
        "effective_date": date(2023, 1, 1),
        "description": "IFRS Foundation standards for sustainability-related financial disclosures.",
        "requirements": [
            ("ISSB-S1", "General Requirements", "General requirements for sustainability-related financial information"),
            ("ISSB-S1-Gov", "Governance (S1)", "Governance processes for sustainability-related risks and opportunities"),
            ("ISSB-S1-Strat", "Strategy (S1)", "Sustainability-related risks and opportunities and their effects"),
            ("ISSB-S1-Risk", "Risk Management (S1)", "Processes to identify and manage sustainability risks"),
            ("ISSB-S1-Metrics", "Metrics & Targets (S1)", "Metrics and targets used to manage sustainability risks"),
            ("ISSB-S2", "Climate-related Disclosures", "Climate-related risks and opportunities"),
            ("ISSB-S2-Gov", "Governance (S2)", "Governance over climate-related risks and opportunities"),
            ("ISSB-S2-Strat", "Strategy (S2)", "Strategy for climate transition and physical risks"),
            ("ISSB-S2-Risk", "Risk Management (S2)", "Climate-related risk management processes"),
            ("ISSB-S2-Metrics", "Metrics & Targets (S2)", "GHG emissions and climate metrics"),
        ],
    },
    {
        "code": "GRI",
        "name": "Global Reporting Initiative Standards",
        "version": "2021",
        "jurisdiction": "Global",
        "effective_date": date(2023, 1, 1),
        "description": "GRI Universal and Topic Standards for sustainability reporting.",
        "requirements": [
            ("GRI-1", "Foundation 2021", "Foundation: purpose, system and reporting principles"),
            ("GRI-2", "General Disclosures 2021", "Organizational details, governance, strategy, policies and practices"),
            ("GRI-3", "Material Topics 2021", "Process for determining material topics and managing impacts"),
            ("GRI-200", "Economic Standards", "Economic performance, market presence and indirect economic impacts"),
            ("GRI-300", "Environmental Standards", "Materials, energy, water, biodiversity, emissions and waste"),
            ("GRI-400", "Social Standards", "Employment, labour practices, human rights, society and product responsibility"),
        ],
    },
    {
        "code": "TCFD",
        "name": "Task Force on Climate-related Financial Disclosures",
        "version": "2023",
        "jurisdiction": "Global",
        "effective_date": date(2017, 6, 29),
        "description": "TCFD recommendations for climate-related financial risk disclosures.",
        "requirements": [
            ("TCFD-GOV-A", "Board Oversight", "Board oversight of climate-related risks and opportunities"),
            ("TCFD-GOV-B", "Management Role", "Management's role in assessing and managing climate risks"),
            ("TCFD-STRAT-A", "Climate Risks & Opportunities", "Short, medium and long-term climate risks and opportunities"),
            ("TCFD-STRAT-B", "Business Impact", "Impact on business, strategy and financial planning"),
            ("TCFD-STRAT-C", "Climate Scenarios", "Resilience of strategy under different climate scenarios"),
            ("TCFD-RISK-A", "Risk Identification", "Processes for identifying and assessing climate risks"),
            ("TCFD-RISK-B", "Risk Management", "Processes for managing climate risks"),
            ("TCFD-RISK-C", "Risk Integration", "Integration of climate risk into overall risk management"),
            ("TCFD-METRICS-A", "Metrics", "Metrics used to assess climate risks and opportunities"),
            ("TCFD-METRICS-B", "Scope 1/2/3 Emissions", "Scope 1, 2 and 3 GHG emissions and targets"),
            ("TCFD-METRICS-C", "Climate Targets", "Targets used to manage climate risks and performance"),
        ],
    },
]


async def seed_disclosure_frameworks(session: AsyncSession) -> None:
    """Seed disclosure frameworks and requirements. Idempotent."""
    fw_repo = SQLDisclosureFrameworkRepository(session)
    req_repo = SQLDisclosureRequirementRepository(session)

    for fw_data in _FRAMEWORKS:
        existing = await fw_repo.get_by_code(fw_data["code"])
        if existing is not None:
            continue

        fw = DisclosureFramework(
            code=fw_data["code"],
            name=fw_data["name"],
            fw_version=fw_data["version"],
            jurisdiction=fw_data["jurisdiction"],
            effective_date=fw_data.get("effective_date"),
            description=fw_data.get("description", ""),
            status=EntityStatus.ACTIVE,
        )
        await fw_repo.save(fw)

        for ref, title, desc in fw_data["requirements"]:
            req = DisclosureRequirement(
                framework_id=fw.id,
                reference=ref,
                title=title,
                description=desc,
                category=_infer_category(ref),
                status=EntityStatus.ACTIVE,
            )
            await req_repo.save(req)


def _infer_category(reference: str) -> str:
    ref_upper = reference.upper()
    # Check full segment tokens to avoid false matches ("-S" matching "ISSB-S2")
    segments = set(ref_upper.replace("-", " ").split())
    if segments & {"E1", "E2", "E3", "E4", "E5", "300", "S2"} or any(
        x in ref_upper for x in ("CLIMATE", "ENVIRON", "WATER", "BIO", "CIRCULAR", "EMISS", "CSRD-E")
    ):
        return "Environmental"
    if segments & {"S1", "S3", "S4", "400"} or any(
        x in ref_upper for x in ("SOCIAL", "WORKFORCE", "COMMUNITY", "CONSUMER", "CSRD-S")
    ):
        return "Social"
    if any(x in ref_upper for x in ("GOV", "CONDUCT", "BOARD", "STRAT", "METRICS", "GRI-1", "GRI-2", "200", "CSRD-G", "GEN")):
        return "Governance"
    return "General"

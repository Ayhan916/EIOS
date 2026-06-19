from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Regulation(BaseEntity):
    """A regulatory framework or directive (e.g. CSRD, ISSB, TCFD)."""

    code: str
    name: str
    jurisdiction: str = "Global"
    reg_version: str = "1.0"  # named reg_version to avoid collision with BaseEntity.version (int)
    effective_date: date | None = None
    reg_status: str = "active"  # active / draft / superseded
    description: str = ""


@dataclass(slots=True, kw_only=True)
class RegulationRequirement(BaseEntity):
    """A specific obligation within a Regulation, stored in the DB for mapping."""

    regulation_id: str
    code: str  # e.g. "CSRD-Art-19a", "ESRS-E1-1", "ISSB-S2-10"
    reference: str  # e.g. "Art. 19a", "ESRS E1-1"
    title: str
    description: str = ""
    category: str = ""  # "Environmental" / "Social" / "Governance"
    pillar: str = ""  # "E" / "S" / "G"
    severity: str = "Medium"  # Low / Medium / High / Critical
    obligation_type: str = "mandatory"  # mandatory / recommended
    keywords: list[str] = field(default_factory=list)

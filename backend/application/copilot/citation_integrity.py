"""Citation Integrity Service — M33.2.

Validates every citation in a Copilot answer:
  - object exists in the platform
  - object belongs to the correct tenant
  - object was part of the retrieved set (in citation_map)

Produces a CopilotCitationIntegrity record per citation, stored in the DB
so auditors can verify citation provenance at any future point.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.copilot_audit import CopilotCitationIntegrity
from domain.enums import CitationIntegrityStatus, EntityStatus

logger = structlog.get_logger(__name__)

# Map citation type → table name for existence checks
_CITATION_TABLE_MAP: dict[str, str] = {
    "Supplier": "suppliers",
    "Finding": "findings",
    "Risk": "risks",
    "Recommendation": "recommendations",
    "Evidence": "evidences",
    "Assessment": "assessments",
    "ComplianceGap": "compliance_gaps",
    "Disclosure": "disclosure_responses",
    "Report": "due_diligence_reports",
}


def _citation_hash(citation_type: str, object_id: str, org_id: str) -> str:
    payload = f"{citation_type}:{object_id}:{org_id}"
    return hashlib.sha256(payload.encode()).hexdigest()


async def verify_citations(
    message_id: str,
    citations: list[dict],
    citation_map: dict[str, str],
    org_id: str,
    session: AsyncSession,
) -> list[CopilotCitationIntegrity]:
    """Validate each citation and return integrity records.

    Checks:
    1. Citation type is in the allowed map
    2. Object ID was in the retrieved citation_map (already enforced by extractor)
    3. Object still exists in the correct tenant's table
    """
    records: list[CopilotCitationIntegrity] = []
    now = datetime.now(UTC)

    for citation in citations:
        ctype = citation.get("citation_type", "")
        obj_id = citation.get("object_id", "")
        table = _CITATION_TABLE_MAP.get(ctype)

        chash = _citation_hash(ctype, obj_id, org_id)

        if table is None:
            # Unknown type — should not happen post-M33.1 hardening, but defensive
            records.append(CopilotCitationIntegrity(
                message_id=message_id,
                organization_id=org_id,
                citation_type=ctype,
                object_id=obj_id,
                integrity_status=CitationIntegrityStatus.DELETED,
                citation_hash=chash,
                citation_snapshot={},
                verified_at=now,
                status=EntityStatus.ACTIVE,
            ))
            continue

        # Check existence and tenant ownership
        try:
            row = await session.execute(
                text(f"SELECT id, organization_id, updated_at FROM {table} WHERE id = :id"),
                {"id": obj_id},
            )
            result = row.mappings().first()
        except Exception:
            result = None

        if result is None:
            status = CitationIntegrityStatus.DELETED
            snapshot: dict = {}
        elif str(result.get("organization_id", "")) != org_id:
            # Object exists but belongs to another tenant — treat as deleted/inaccessible
            status = CitationIntegrityStatus.DELETED
            snapshot = {}
            logger.warning(
                "citation_cross_tenant",
                citation_type=ctype,
                object_id=obj_id,
                expected_org=org_id,
            )
        else:
            status = CitationIntegrityStatus.VERIFIED
            snapshot = {
                "id": obj_id,
                "organization_id": org_id,
                "updated_at": str(result.get("updated_at", "")),
            }

        records.append(CopilotCitationIntegrity(
            message_id=message_id,
            organization_id=org_id,
            citation_type=ctype,
            object_id=obj_id,
            integrity_status=status,
            citation_hash=chash,
            citation_snapshot=snapshot,
            verified_at=now,
            status=EntityStatus.ACTIVE,
        ))

    return records

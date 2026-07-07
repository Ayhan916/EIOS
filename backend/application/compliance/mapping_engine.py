"""Requirement Mapping Engine.

Creates RequirementMapping records that link Findings, Risks, and
Recommendations to RegulationRequirements.

Supports two mapping methods:
  - manual:     user explicitly creates a mapping via the API
  - rule_based: keywords from the entity text match requirement keywords
                (same approach as the existing coverage engine, but stored)

Explainability: every mapping records rationale + confidence + method + version,
so the provenance chain (entity → requirement → rationale) is always available.
"""

from __future__ import annotations

from datetime import UTC, datetime

from domain.enums import EntityStatus
from domain.regulation import RegulationRequirement
from domain.requirement_mapping import RequirementMapping

_MAPPING_VERSION = "1.0"

# Confidence thresholds for rule-based matching
_HIGH_CONFIDENCE = 0.85  # ≥2 keyword matches
_LOW_CONFIDENCE = 0.65  # 1 keyword match


def _keywords_match(text: str, keywords: list[str]) -> tuple[bool, int]:
    """Return (any_match, match_count)."""
    lower = text.lower()
    count = sum(1 for kw in keywords if kw.lower() in lower)
    return count > 0, count


def create_manual_mapping(
    organization_id: str,
    regulation_requirement_id: str,
    entity_type: str,
    entity_id: str,
    rationale: str,
    confidence: float = 0.9,
    supplier_id: str | None = None,
    assessment_id: str | None = None,
    created_by: str | None = None,
    regulation_version: str = "1.0",
) -> RequirementMapping:
    return RequirementMapping(
        organization_id=organization_id,
        regulation_requirement_id=regulation_requirement_id,
        entity_type=entity_type,
        entity_id=entity_id,
        confidence=max(0.0, min(1.0, confidence)),
        rationale=rationale or "Manually mapped by user.",
        mapping_method="manual",
        mapping_version=_MAPPING_VERSION,
        regulation_version_at_mapping=regulation_version,
        mapped_at=datetime.now(UTC),
        supplier_id=supplier_id,
        assessment_id=assessment_id,
        status=EntityStatus.ACTIVE,
        created_by=created_by,
    )


def auto_map_entity(
    organization_id: str,
    entity_type: str,
    entity_id: str,
    entity_text: str,
    requirements: list[RegulationRequirement],
    supplier_id: str | None = None,
    assessment_id: str | None = None,
    regulation_version_by_id: dict[str, str] | None = None,
) -> list[RequirementMapping]:
    """Rule-based auto-mapping: scan entity text against requirement keywords.

    Returns RequirementMapping objects (not yet persisted) for each requirement
    whose keywords appear in entity_text. Caller is responsible for dedup-checking
    before saving (use RequirementMappingRepository.exists()).
    """
    now = datetime.now(UTC)
    _versions = regulation_version_by_id or {}
    mappings: list[RequirementMapping] = []

    for req in requirements:
        matched, count = _keywords_match(entity_text, req.keywords)
        if not matched:
            continue
        confidence = _HIGH_CONFIDENCE if count >= 2 else _LOW_CONFIDENCE
        matched_kws = [kw for kw in req.keywords if kw.lower() in entity_text.lower()]
        rationale = (
            f"Rule-based match on {len(matched_kws)} keyword(s): "
            + ", ".join(f'"{k}"' for k in matched_kws[:5])
            + f". Requirement: {req.reference} — {req.title}."
        )
        mappings.append(
            RequirementMapping(
                organization_id=organization_id,
                regulation_requirement_id=req.id,
                entity_type=entity_type,
                entity_id=entity_id,
                confidence=confidence,
                rationale=rationale,
                mapping_method="rule_based",
                mapping_version=_MAPPING_VERSION,
                regulation_version_at_mapping=_versions.get(req.regulation_id, "1.0"),
                mapped_at=now,
                supplier_id=supplier_id,
                assessment_id=assessment_id,
                status=EntityStatus.ACTIVE,
            )
        )

    return mappings

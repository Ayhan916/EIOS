"""Tests for E4-F1 ConfidenceCard Standardisierung (ADR-015).

Covers:
  - ConfidenceCard value object invariants
  - build_confidence_card_from_level helper
  - ConfidenceCardOut Pydantic schema (from_attributes, overall_level, limitations)
  - FindingResponse and RiskResponse expose confidence_card
"""

from __future__ import annotations

import pytest

from domain.enums import ConfidenceLevel
from domain.value_objects import ConfidenceCard

pytestmark = pytest.mark.unit


# ── ConfidenceCard value object ───────────────────────────────────────────────

class TestConfidenceCardValueObject:
    def test_frozen(self) -> None:
        card = ConfidenceCard(level=ConfidenceLevel.HIGH, score=0.85, basis="test")
        with pytest.raises((AttributeError, TypeError)):
            card.score = 0.0  # type: ignore[misc]

    def test_score_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError):
            ConfidenceCard(level=ConfidenceLevel.HIGH, score=1.5, basis="x")

    def test_limitations_defaults_to_empty_tuple(self) -> None:
        card = ConfidenceCard(level=ConfidenceLevel.MEDIUM, score=0.6, basis="b")
        assert card.limitations == ()

    def test_limitations_stored_as_tuple(self) -> None:
        card = ConfidenceCard(
            level=ConfidenceLevel.LOW, score=0.3, basis="x",
            limitations=("gap1", "gap2"),
        )
        assert "gap1" in card.limitations
        assert len(card.limitations) == 2


# ── build_confidence_card_from_level ─────────────────────────────────────────

class TestBuildConfidenceCardFromLevel:
    def test_high_returns_high_score(self) -> None:
        from application.confidence_calculator import build_confidence_card_from_level
        card = build_confidence_card_from_level(ConfidenceLevel.HIGH)
        assert card.level == ConfidenceLevel.HIGH
        assert card.score >= 0.75

    def test_medium_returns_medium_score(self) -> None:
        from application.confidence_calculator import build_confidence_card_from_level
        card = build_confidence_card_from_level(ConfidenceLevel.MEDIUM)
        assert card.level == ConfidenceLevel.MEDIUM
        assert 0.45 <= card.score < 0.75

    def test_low_returns_low_score(self) -> None:
        from application.confidence_calculator import build_confidence_card_from_level
        card = build_confidence_card_from_level(ConfidenceLevel.LOW)
        assert card.level == ConfidenceLevel.LOW
        assert card.score < 0.45

    def test_returns_confidence_card_instance(self) -> None:
        from application.confidence_calculator import build_confidence_card_from_level
        card = build_confidence_card_from_level(ConfidenceLevel.HIGH)
        assert isinstance(card, ConfidenceCard)

    def test_basis_is_non_empty(self) -> None:
        from application.confidence_calculator import build_confidence_card_from_level
        card = build_confidence_card_from_level(ConfidenceLevel.MEDIUM)
        assert card.basis


# ── ConfidenceCardOut Pydantic schema ─────────────────────────────────────────

class TestConfidenceCardOut:
    def test_model_validate_from_domain_card(self) -> None:
        from interfaces.api.schemas.finding import ConfidenceCardOut
        card = ConfidenceCard(level=ConfidenceLevel.HIGH, score=0.85, basis="x")
        out = ConfidenceCardOut.model_validate(card, from_attributes=True)
        assert out.level == "High"
        assert out.score == 0.85

    def test_overall_level_equals_level(self) -> None:
        from interfaces.api.schemas.finding import ConfidenceCardOut
        card = ConfidenceCard(level=ConfidenceLevel.MEDIUM, score=0.6, basis="x")
        out = ConfidenceCardOut.model_validate(card, from_attributes=True)
        assert out.overall_level == out.level

    def test_limitations_converted_to_list(self) -> None:
        from interfaces.api.schemas.finding import ConfidenceCardOut
        card = ConfidenceCard(
            level=ConfidenceLevel.LOW, score=0.3, basis="x",
            limitations=("missing scope 3", "no third-party audit"),
        )
        out = ConfidenceCardOut.model_validate(card, from_attributes=True)
        assert isinstance(out.limitations, list)
        assert "missing scope 3" in out.limitations

    def test_from_card_classmethod(self) -> None:
        from interfaces.api.schemas.finding import ConfidenceCardOut
        card = ConfidenceCard(level=ConfidenceLevel.HIGH, score=0.85, basis="test")
        out = ConfidenceCardOut.from_card(card)
        assert out.level == "High"
        assert out.overall_level == "High"

    def test_no_confidence_as_bare_float(self) -> None:
        """DoD: confidence must never be just a bare float — always ConfidenceCardOut."""
        from interfaces.api.schemas.finding import FindingResponse
        # FindingResponse must have confidence_card field, not just a float
        assert "confidence_card" in FindingResponse.model_fields

    def test_risk_response_has_confidence_card(self) -> None:
        from interfaces.api.schemas.risk import RiskResponse
        assert "confidence_card" in RiskResponse.model_fields


# ── Finding domain entity ─────────────────────────────────────────────────────

class TestFindingConfidenceCard:
    def test_finding_has_confidence_card_field(self) -> None:
        from domain.finding import Finding
        import inspect
        fields = {f.name for f in Finding.__dataclass_fields__.values()}
        assert "confidence_card" in fields

    def test_finding_confidence_card_defaults_none(self) -> None:
        from domain.finding import Finding
        from domain.base_entity import BaseEntity
        import uuid
        from datetime import datetime, UTC
        from domain.enums import EntityStatus

        f = Finding(
            id=str(uuid.uuid4()),
            title="T", description="D", assessment_id="a1",
            status=EntityStatus.ACTIVE, version=1,
            owner=None, created_by=None, updated_by=None,
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        assert f.confidence_card is None


# ── Risk domain entity ────────────────────────────────────────────────────────

class TestRiskConfidenceCard:
    def test_risk_has_confidence_card_field(self) -> None:
        from domain.risk import Risk
        fields = {f.name for f in Risk.__dataclass_fields__.values()}
        assert "confidence_card" in fields

"""Tests for application/audit_package_service.py — E5-F2.

Unit tests mock the DB session to verify:
  - AuditPackage is returned with correct structure
  - generator_version is "AuditPackage-v1.0"
  - methodology contains formula_version = FORMULA_VERSION from E2-F1
  - methodology contains extraction_model and main_model as passed
  - period_from < period_to constraint (business rule enforced in API layer)
  - AuditPackage is frozen (Value Object)
  - supplier with no assessments → assessment_ids=() and counts=0
  - risk score derived from SupplierScoreModel.inputs when present
  - risk score defaults to 0.0 when no SupplierScoreModel exists
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.audit_package_service import AuditPackageService, _GENERATOR_VERSION
from application.scoring.risk_score_calculator import FORMULA_VERSION
from domain.audit_package import AuditPackage

pytestmark = pytest.mark.unit

_PERIOD_FROM = datetime(2025, 1, 1, tzinfo=UTC)
_PERIOD_TO = datetime(2025, 12, 31, tzinfo=UTC)
_SUPPLIER_ID = "sup-test-999"
_EXTRACTION_MODEL = "claude-haiku-4-5-20251001"
_MAIN_MODEL = "claude-sonnet-4-6"


# ── session mock factory ──────────────────────────────────────────────────────

def _make_session(
    assessment_ids: list[str] | None = None,
    finding_ids: list[str] | None = None,
    findings_count: int = 0,
    evidence_count: int = 0,
    risks_count: int = 0,
    audit_event_count: int = 0,
    score_inputs: dict | None = None,
) -> AsyncMock:
    session = AsyncMock()

    call_results = []

    # Assessment IDs
    r_assess = MagicMock()
    r_assess.scalars.return_value.all.return_value = assessment_ids or []
    call_results.append(r_assess)

    if assessment_ids:
        # findings count
        r_fc = MagicMock()
        r_fc.scalar_one.return_value = findings_count
        call_results.append(r_fc)

        # finding IDs
        r_fids = MagicMock()
        r_fids.scalars.return_value.all.return_value = finding_ids or []
        call_results.append(r_fids)

        if finding_ids:
            # evidence count
            r_ev = MagicMock()
            r_ev.scalar_one.return_value = evidence_count
            call_results.append(r_ev)

        # risks count
        r_rc = MagicMock()
        r_rc.scalar_one.return_value = risks_count
        call_results.append(r_rc)

    # Audit events count
    r_ae = MagicMock()
    r_ae.scalar_one.return_value = audit_event_count
    call_results.append(r_ae)

    # SupplierScoreModel row
    if score_inputs is not None:
        score_model = MagicMock()
        score_model.inputs = score_inputs
    else:
        score_model = None
    r_score = MagicMock()
    r_score.scalar_one_or_none.return_value = score_model
    call_results.append(r_score)

    # PromptRegistry calls (get_active × 2)
    r_pv1 = MagicMock()
    r_pv1.scalar_one_or_none.return_value = None
    r_pv2 = MagicMock()
    r_pv2.scalar_one_or_none.return_value = None
    call_results.extend([r_pv1, r_pv2])

    session.execute = AsyncMock(side_effect=call_results)
    return session


# ── core structure ────────────────────────────────────────────────────────────

class TestAuditPackageStructure:
    @pytest.mark.asyncio
    async def test_returns_audit_package(self) -> None:
        session = _make_session()
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert isinstance(result, AuditPackage)

    @pytest.mark.asyncio
    async def test_generator_version(self) -> None:
        session = _make_session()
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.generator_version == _GENERATOR_VERSION == "AuditPackage-v1.0"

    @pytest.mark.asyncio
    async def test_package_id_is_uuid_string(self) -> None:
        import re
        session = _make_session()
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert re.match(r"[0-9a-f-]{36}", result.package_id)

    @pytest.mark.asyncio
    async def test_supplier_id_and_period_preserved(self) -> None:
        session = _make_session()
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.supplier_id == _SUPPLIER_ID
        assert result.period_from == _PERIOD_FROM
        assert result.period_to == _PERIOD_TO

    @pytest.mark.asyncio
    async def test_result_is_frozen(self) -> None:
        session = _make_session()
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        with pytest.raises((AttributeError, TypeError)):
            result.findings_count = 999  # type: ignore[misc]


# ── methodology snapshot ──────────────────────────────────────────────────────

class TestMethodologySnapshot:
    @pytest.mark.asyncio
    async def test_formula_version_matches_e2f1(self) -> None:
        session = _make_session()
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.methodology.formula_version == FORMULA_VERSION

    @pytest.mark.asyncio
    async def test_extraction_model_from_constructor(self) -> None:
        session = _make_session()
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.methodology.extraction_model == _EXTRACTION_MODEL

    @pytest.mark.asyncio
    async def test_main_model_from_constructor(self) -> None:
        session = _make_session()
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.methodology.main_model == _MAIN_MODEL


# ── counts ────────────────────────────────────────────────────────────────────

class TestCounts:
    @pytest.mark.asyncio
    async def test_no_assessments_gives_zero_counts(self) -> None:
        session = _make_session(assessment_ids=[])
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.assessment_ids == ()
        assert result.findings_count == 0
        assert result.risks_count == 0
        assert result.evidence_count == 0

    @pytest.mark.asyncio
    async def test_assessment_ids_passed_through(self) -> None:
        ids = ["ass-1", "ass-2"]
        session = _make_session(assessment_ids=ids, finding_ids=[])
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert set(result.assessment_ids) == set(ids)

    @pytest.mark.asyncio
    async def test_audit_event_count_mapped(self) -> None:
        session = _make_session(audit_event_count=17)
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.audit_event_count == 17


# ── risk score ────────────────────────────────────────────────────────────────

class TestRiskScore:
    @pytest.mark.asyncio
    async def test_defaults_to_zero_when_no_score_model(self) -> None:
        session = _make_session(score_inputs=None)
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.risk_score == 0.0
        assert result.risk_band == "Low"

    @pytest.mark.asyncio
    async def test_risk_score_computed_from_inputs(self) -> None:
        # critical_findings=10 → raw=200 → score=40.0 → MODERATE
        score_inputs = {"critical_findings": 10, "total_assessments": 1}
        session = _make_session(score_inputs=score_inputs)
        svc = AuditPackageService(session, _EXTRACTION_MODEL, _MAIN_MODEL)
        result = await svc.generate(_SUPPLIER_ID, _PERIOD_FROM, _PERIOD_TO)
        assert result.risk_score == 40.0
        assert result.risk_band == "Moderate"

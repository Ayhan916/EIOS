"""M33.2 — Security Hardening & Tenant Isolation Tests.

Verifies:
- Citations never reference objects outside the retrieved scope
- Cross-tenant access is blocked at every audit boundary
- Confidence scores are evidence-based (never raw model confidence)
- Contradiction detection does not leak cross-retriever data
- Audit package org_id always matches the requesting org
"""

from __future__ import annotations

from application.copilot.audit_package_service import (
    build_audit_payload,
    compute_package_hash,
    create_audit_package,
)
from application.copilot.citation_extractor import extract_citations
from application.copilot.confidence_calculator import calculate_confidence
from application.copilot.contradiction_detector import detect_contradictions
from application.copilot.freshness_tracker import FreshnessReport, analyze_freshness
from application.copilot.retrieval.base import RetrievalResult
from domain.copilot import CopilotMessage
from domain.enums import CopilotConfidenceLevel, EntityStatus


def _msg(**kwargs) -> CopilotMessage:
    defaults = dict(
        conversation_id="conv-1",
        organization_id="org-1",
        user_id="user-1",
        role="assistant",
        content="Answer",
        intent="general",
        citations=[],
        model_used="openai:gpt-4o",
        generation_ms=1000,
        retrieval_snapshot={},
        assembled_context="",
        system_prompt_snapshot="",
        confidence_level="",
        confidence_factors={},
        freshness_summary={},
        contradiction_count=0,
        context_budget_used=0,
        context_truncated=False,
        status=EntityStatus.ACTIVE,
    )
    defaults.update(kwargs)
    return CopilotMessage(**defaults)


class TestCitationScopeIsolation:
    def test_citation_outside_retrieved_scope_rejected(self):
        """No citation referencing an ID not in citation_map should be accepted."""
        content = "[Supplier:outside-scope-id] is mentioned."
        citation_map = {"in-scope-id": "Supplier"}
        citations = extract_citations(content, citation_map)
        assert not any(c["object_id"] == "outside-scope-id" for c in citations)

    def test_only_retrieved_ids_accepted(self):
        """Only IDs present in citation_map survive extraction."""
        content = "[Supplier:s1][Supplier:s2][Finding:hallucinated-f99]"
        citation_map = {"s1": "Supplier", "s2": "Supplier"}
        citations = extract_citations(content, citation_map)
        obj_ids = {c["object_id"] for c in citations}
        assert "s1" in obj_ids
        assert "s2" in obj_ids
        assert "hallucinated-f99" not in obj_ids

    def test_empty_citation_map_rejects_everything(self):
        """With an empty citation_map, no citations should be accepted."""
        content = "[Supplier:s1][Finding:f1][Risk:r1]"
        citations = extract_citations(content, {})
        assert citations == []

    def test_only_in_scope_ids_accepted_regardless_of_bracket_type(self):
        """The extractor validates object_id presence in citation_map.
        Only IDs from retrieved scope are accepted.
        """
        content = "[Supplier:not-retrieved-id][Finding:also-not-retrieved]"
        citation_map = {"retrieved-id": "Supplier"}
        citations = extract_citations(content, citation_map)
        obj_ids = {c["object_id"] for c in citations}
        assert "not-retrieved-id" not in obj_ids
        assert "also-not-retrieved" not in obj_ids


class TestConfidenceNeverRawModelScore:
    def test_confidence_level_is_enum_value(self):
        """Confidence must be one of the four evidence-based levels."""
        valid_levels = {l.value for l in CopilotConfidenceLevel}
        results = [RetrievalResult(
            retriever="supplier_retriever",
            provenance="test",
            data=[{"id": "s1"}],
            source_ids=["s1"],
            citation_type="Supplier",
        )]
        level, _ = calculate_confidence(results, [], [], FreshnessReport())
        assert level.value in valid_levels

    def test_confidence_factors_have_no_model_probability(self):
        """The factors dict must not contain raw model probability fields."""
        results = [RetrievalResult(
            retriever="supplier_retriever",
            provenance="test",
            data=[{"id": "s1"}],
            source_ids=["s1"],
            citation_type="Supplier",
        )]
        _, factors = calculate_confidence(results, [], [], FreshnessReport())
        forbidden_keys = {"model_confidence", "llm_probability", "model_score", "raw_model_score"}
        assert not forbidden_keys.intersection(factors.keys())

    def test_empty_retrieval_gives_low_not_none(self):
        """Even with no data, confidence must still return a valid level (LOW)."""
        level, factors = calculate_confidence([], [], [], FreshnessReport())
        assert level in CopilotConfidenceLevel
        assert level == CopilotConfidenceLevel.LOW


class TestAuditPackageTenantIsolation:
    def test_audit_package_org_matches_assistant_message(self):
        user_msg = _msg(role="user", content="Q", organization_id="org-42")
        asst_msg = _msg(organization_id="org-42")
        pkg = create_audit_package(user_msg, asst_msg, [], {}, {})
        assert pkg.organization_id == "org-42"

    def test_audit_payload_org_matches_message(self):
        user_msg = _msg(role="user", content="Q", organization_id="org-55")
        asst_msg = _msg(organization_id="org-55")
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert payload["organization_id"] == "org-55"

    def test_audit_hash_covers_org_id(self):
        """Changing org_id changes the hash — org_id is part of the canonical payload."""
        user_msg = _msg(role="user", content="Q", organization_id="org-A")
        asst_msg_a = _msg(organization_id="org-A")
        asst_msg_b = _msg(organization_id="org-B")

        payload_a = build_audit_payload(user_msg, asst_msg_a, [], {}, {})
        payload_b = build_audit_payload(user_msg, asst_msg_b, [], {}, {})

        # Hash must differ when org_id differs (after normalizing generated_at)
        # Compare content hash excluding dynamic timestamp
        payload_a_stable = {k: v for k, v in payload_a.items() if k != "generated_at"}
        payload_b_stable = {k: v for k, v in payload_b.items() if k != "generated_at"}
        assert compute_package_hash(payload_a_stable) != compute_package_hash(payload_b_stable)


class TestContradictionIsolation:
    def test_contradictions_only_from_current_retrieval(self):
        """detect_contradictions only looks at passed-in results — no global state."""
        clean_results = [
            RetrievalResult(
                retriever="supplier_retriever",
                provenance="test",
                data=[{"supplier_id": "s1", "risk_band": "High", "critical_findings": []}],
                source_ids=["s1"],
                citation_type="Supplier",
            )
        ]
        contradictions = detect_contradictions(clean_results)
        types = [c.contradiction_type for c in contradictions]
        # No critical gaps in these results, so no RISK_VS_COMPLIANCE
        assert "risk_vs_compliance" not in types

    def test_contradictions_not_persisted_to_global_state(self):
        """Calling detect_contradictions twice with different data gives independent results."""
        risky = [
            RetrievalResult(
                retriever="supplier_retriever",
                provenance="test",
                data=[{"supplier_id": "s1", "risk_band": "Low", "critical_findings": []}],
                source_ids=["s1"],
                citation_type="Supplier",
            ),
            RetrievalResult(
                retriever="compliance_retriever",
                provenance="test",
                data=[{"gap_id": "g1", "severity": "Critical"}],
                source_ids=["g1"],
                citation_type="ComplianceGap",
            ),
        ]
        clean = []

        with_contradictions = detect_contradictions(risky)
        without_contradictions = detect_contradictions(clean)

        assert len(with_contradictions) > 0
        assert len(without_contradictions) == 0


class TestFreshnessIsolation:
    def test_freshness_only_from_passed_results(self):
        """analyze_freshness doesn't mix data from different calls."""
        from datetime import UTC, datetime, timedelta

        retrieved_at = datetime.now(UTC).isoformat()
        old_ts = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        new_ts = (datetime.now(UTC) - timedelta(days=1)).isoformat()

        r1 = RetrievalResult(
            retriever="supplier_retriever",
            provenance="test",
            data=[{"id": "s1"}],
            source_ids=["s1"],
            citation_type="Supplier",
            freshness_metadata=[{
                "object_id": "s1",
                "object_type": "S",
                "updated_at": old_ts,
                "retrieved_at": retrieved_at,
            }],
        )
        r2 = RetrievalResult(
            retriever="supplier_retriever",
            provenance="test",
            data=[{"id": "s2"}],
            source_ids=["s2"],
            citation_type="Supplier",
            freshness_metadata=[{
                "object_id": "s2",
                "object_type": "S",
                "updated_at": new_ts,
                "retrieved_at": retrieved_at,
            }],
        )

        report_old = analyze_freshness([r1])
        report_new = analyze_freshness([r2])

        assert report_old.average_age_days > report_new.average_age_days

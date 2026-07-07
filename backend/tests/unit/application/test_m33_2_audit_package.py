"""M33.2 — Copilot Audit Package Tests.

Verifies canonical JSON hashing, payload structure, determinism,
and tamper detection for the audit package.
"""

from __future__ import annotations

import hashlib
import json

from application.copilot.audit_package_service import (
    build_audit_payload,
    compute_package_hash,
    create_audit_package,
)
from domain.copilot import CopilotMessage
from domain.enums import AuditVerificationStatus, CopilotMessageRole, EntityStatus


def _make_message(role: str = CopilotMessageRole.ASSISTANT, **kwargs) -> CopilotMessage:
    defaults = dict(
        conversation_id="conv-1",
        organization_id="org-1",
        user_id="user-1",
        role=role,
        content="Test answer about ESG performance.",
        intent="general",
        citations=[{"citation_type": "Supplier", "object_id": "s1", "relevance": "explicit"}],
        model_used="openai:gpt-4o",
        generation_ms=1500,
        retrieval_snapshot={"supplier_retriever": {"source_ids": ["s1"], "count": 1}},
        assembled_context="[SUPPLIER_RETRIEVER] Supplier data...",
        system_prompt_snapshot="You are the EIOS AI Copilot...",
        confidence_level="High",
        confidence_factors={"raw_score": 70.0},
        freshness_summary={"average_age_days": 3.0},
        contradiction_count=0,
        context_budget_used=5000,
        context_truncated=False,
        status=EntityStatus.ACTIVE,
    )
    defaults.update(kwargs)
    return CopilotMessage(**defaults)


class TestCanonicalJsonHash:
    def test_hash_is_deterministic(self):
        payload = {"z_key": "value_z", "a_key": "value_a", "nested": {"b": 1, "a": 2}}
        h1 = compute_package_hash(payload)
        h2 = compute_package_hash(payload)
        assert h1 == h2

    def test_hash_ignores_dict_insertion_order(self):
        payload_a = {"a": 1, "b": 2}
        payload_b = {"b": 2, "a": 1}
        assert compute_package_hash(payload_a) == compute_package_hash(payload_b)

    def test_hash_is_sha256(self):
        payload = {"key": "value"}
        h = compute_package_hash(payload)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_changes_when_payload_changes(self):
        payload = {"answer": "original answer"}
        tampered = {"answer": "tampered answer"}
        assert compute_package_hash(payload) != compute_package_hash(tampered)

    def test_hash_is_sha256_of_canonical_json(self):
        payload = {"b": 2, "a": 1}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        expected = hashlib.sha256(canonical).hexdigest()
        assert compute_package_hash(payload) == expected


class TestBuildAuditPayload:
    def test_payload_has_schema_version(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="What is our ESG score?")
        asst_msg = _make_message()
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert payload["schema_version"] == "1.0"

    def test_payload_contains_question(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="What is our ESG score?")
        asst_msg = _make_message()
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert payload["question"] == "What is our ESG score?"

    def test_payload_contains_answer(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message(content="Definitive answer here.")
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert payload["answer"] == "Definitive answer here."

    def test_payload_contains_citations(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message()
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert len(payload["citations"]) == 1
        assert payload["citations"][0]["object_id"] == "s1"

    def test_payload_contains_confidence(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message(confidence_level="Very High")
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert payload["confidence_level"] == "Very High"

    def test_payload_contains_contradictions(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message()
        contradictions = [{"contradiction_type": "risk_vs_compliance", "description": "Mismatch"}]
        payload = build_audit_payload(user_msg, asst_msg, contradictions, {}, {})
        assert payload["contradictions"] == contradictions

    def test_payload_contains_retrieval_snapshot(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message()
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert "supplier_retriever" in payload["retrieval_snapshot"]

    def test_payload_contains_prompt_snapshot(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message()
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert "You are the EIOS AI Copilot" in payload["system_prompt_snapshot"]

    def test_payload_contains_org_id(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message(organization_id="org-99")
        payload = build_audit_payload(user_msg, asst_msg, [], {}, {})
        assert payload["organization_id"] == "org-99"


class TestCreateAuditPackage:
    def test_package_has_valid_hash(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message()
        pkg = create_audit_package(user_msg, asst_msg, [], {}, {})
        recomputed = compute_package_hash(pkg.json_payload)
        assert pkg.package_hash == recomputed

    def test_package_status_pending(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message()
        pkg = create_audit_package(user_msg, asst_msg, [], {}, {})
        assert pkg.verification_status == AuditVerificationStatus.PENDING

    def test_package_message_id_matches(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message()
        pkg = create_audit_package(user_msg, asst_msg, [], {}, {})
        assert pkg.message_id == asst_msg.id

    def test_package_org_id_matches(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message(organization_id="org-42")
        pkg = create_audit_package(user_msg, asst_msg, [], {}, {})
        assert pkg.organization_id == "org-42"

    def test_tamper_detection_hash_mismatch(self):
        user_msg = _make_message(role=CopilotMessageRole.USER, content="Q")
        asst_msg = _make_message()
        pkg = create_audit_package(user_msg, asst_msg, [], {}, {})
        original_hash = pkg.package_hash

        # Simulate tampering
        pkg.json_payload["answer"] = "TAMPERED ANSWER"
        recomputed = compute_package_hash(pkg.json_payload)
        assert recomputed != original_hash

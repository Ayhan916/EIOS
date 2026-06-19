"""Copilot Audit Package Service — M33.2.

Generates an immutable, hash-verified audit package (JSON + optional PDF)
capturing the full reasoning chain for every Copilot assistant answer:

  Question → Retrieved Data → Context → Prompt → Model → Answer → Citations

The package_hash allows future tamper detection via the reproducibility verifier.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from domain.copilot import CopilotMessage
from domain.copilot_audit import CopilotAuditPackage
from domain.enums import AuditVerificationStatus, EntityStatus

_SCHEMA_VERSION = "1.0"


def _canonical_json(payload: dict) -> bytes:
    """Deterministic JSON encoding for hashing — sorted keys, no whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def compute_package_hash(payload: dict) -> str:
    """Return sha256 hex digest of the canonical JSON payload."""
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def build_audit_payload(
    user_msg: CopilotMessage,
    assistant_msg: CopilotMessage,
    contradictions: list[dict],
    freshness_summary: dict,
    context_budget: dict,
) -> dict:
    """Assemble the full audit payload dict from the copilot service outputs."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "message_id": assistant_msg.id,
        "user_message_id": user_msg.id,
        "conversation_id": assistant_msg.conversation_id,
        "organization_id": assistant_msg.organization_id,
        "user_id": assistant_msg.user_id,
        # Question
        "question": user_msg.content,
        "intent": assistant_msg.intent,
        # Retrieval + context
        "retrieval_snapshot": assistant_msg.retrieval_snapshot,
        "assembled_context": assistant_msg.assembled_context,
        "context_budget": context_budget,
        # Prompt
        "system_prompt_snapshot": assistant_msg.system_prompt_snapshot,
        # Model + answer
        "model_used": assistant_msg.model_used,
        "generation_ms": assistant_msg.generation_ms,
        "answer": assistant_msg.content,
        # Citations
        "citations": assistant_msg.citations,
        # Explainability
        "confidence_level": assistant_msg.confidence_level,
        "confidence_factors": assistant_msg.confidence_factors,
        "contradictions": contradictions,
        "freshness_summary": freshness_summary,
    }


def create_audit_package(
    user_msg: CopilotMessage,
    assistant_msg: CopilotMessage,
    contradictions: list[dict],
    freshness_summary: dict,
    context_budget: dict,
) -> CopilotAuditPackage:
    """Build and return a CopilotAuditPackage ready for persistence."""
    payload = build_audit_payload(
        user_msg, assistant_msg, contradictions, freshness_summary, context_budget
    )
    pkg_hash = compute_package_hash(payload)

    return CopilotAuditPackage(
        message_id=assistant_msg.id,
        organization_id=assistant_msg.organization_id,
        package_hash=pkg_hash,
        json_payload=payload,
        generated_at=datetime.now(UTC),
        verification_status=AuditVerificationStatus.PENDING,
        verified_at=None,
        status=EntityStatus.ACTIVE,
    )


def generate_audit_pdf(payload: dict) -> bytes:
    """Generate a human-readable PDF audit package using fpdf2."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "EIOS AI COPILOT AUDIT PACKAGE", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Schema Version: {payload.get('schema_version', '?')}", ln=True)
    pdf.cell(0, 6, f"Generated: {payload.get('generated_at', '')}", ln=True)
    pdf.cell(0, 6, f"Message ID: {payload.get('message_id', '')}", ln=True)
    pdf.cell(0, 6, f"Organisation ID: {payload.get('organization_id', '')}", ln=True)
    pdf.ln(4)

    def section(title: str) -> None:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", "", 9)

    def body(text: str, max_chars: int = 2000) -> None:
        safe = str(text)[:max_chars].replace("\x00", "")
        pdf.multi_cell(0, 5, safe)
        pdf.ln(2)

    section("QUESTION")
    body(payload.get("question", ""))

    section("INTENT DETECTED")
    body(payload.get("intent", ""))

    section("CONFIDENCE")
    conf = payload.get("confidence_factors", {})
    body(
        f"Level: {payload.get('confidence_level', '')}\n"
        f"Score: {conf.get('raw_score', '')}\n"
        f"Retrieval Coverage: {conf.get('retrieval_coverage', '')}\n"
        f"Citations: {conf.get('citation_count', '')}\n"
        f"Source Diversity: {conf.get('source_diversity', '')}\n"
        f"Avg Data Age (days): {conf.get('average_data_age_days', '')}\n"
        f"Contradictions: {conf.get('contradiction_count', '')}"
    )

    section("CONTRADICTIONS DETECTED")
    contradictions = payload.get("contradictions", [])
    if contradictions:
        for c in contradictions:
            body(f"[{c.get('contradiction_type')}] {c.get('description', '')}")
    else:
        body("None detected.")

    section("DATA FRESHNESS")
    freshness = payload.get("freshness_summary", {})
    body(
        f"Average age: {freshness.get('average_age_days', 0):.1f} days\n"
        f"Stale retrievers: {', '.join(freshness.get('stale_retrievers', [])) or 'None'}"
    )

    section("CONTEXT BUDGET")
    budget = payload.get("context_budget", {})
    body(
        f"Used: {budget.get('used_chars', 0)} / {budget.get('max_chars', 0)} chars\n"
        f"Truncated: {budget.get('truncated', False)}\n"
        f"Included: {', '.join(budget.get('retrievers_included', []))}\n"
        f"Omitted: {', '.join(budget.get('retrievers_omitted', [])) or 'None'}"
    )

    section("RETRIEVAL SNAPSHOT")
    snapshot = payload.get("retrieval_snapshot", {})
    for retriever, data in snapshot.items():
        ids = data.get("source_ids", [])
        body(f"{retriever}: {len(ids)} object(s) — {', '.join(ids[:5])}")

    section("ASSEMBLED CONTEXT (first 1000 chars)")
    body((payload.get("assembled_context") or "")[:1000])

    section("SYSTEM PROMPT SNAPSHOT (first 500 chars)")
    body((payload.get("system_prompt_snapshot") or "")[:500])

    section("MODEL")
    body(payload.get("model_used", ""))

    section("ANSWER")
    body(payload.get("answer", ""))

    section("CITATIONS")
    citations = payload.get("citations", [])
    if citations:
        for c in citations:
            body(f"[{c.get('citation_type')}:{c.get('object_id')}] relevance={c.get('relevance')}")
    else:
        body("No citations.")

    section("AUDIT HASH (SHA-256)")
    pkg_hash = compute_package_hash(payload)
    body(pkg_hash)

    return bytes(pdf.output())

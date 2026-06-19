"""M33.1 — Citation Validation Hardening Tests.

Verifies that extract_citations() only accepts IDs present in citation_map,
rejecting any LLM-hallucinated source references.
"""

from __future__ import annotations

from application.copilot.citation_extractor import extract_citations


class TestCitationMapValidation:
    def test_valid_explicit_citation_accepted(self):
        """Explicit [Type:id] citation is accepted when id is in citation_map."""
        content = "[Supplier:s-real] has critical issues."
        cmap = {"s-real": "Supplier"}
        citations = extract_citations(content, cmap)
        assert len(citations) == 1
        assert citations[0]["object_id"] == "s-real"
        assert citations[0]["relevance"] == "explicit"

    def test_fake_id_not_in_cmap_rejected(self):
        """LLM-hallucinated ID not in citation_map is silently dropped."""
        content = "[Supplier:hallucinated-id] is the top risk supplier."
        cmap = {"real-id": "Supplier"}
        citations = extract_citations(content, cmap)
        assert not any(c["object_id"] == "hallucinated-id" for c in citations)

    def test_fake_id_empty_cmap_rejected(self):
        """Explicit citation with empty citation_map is always rejected."""
        content = "[Finding:f-999] references a non-existent finding."
        citations = extract_citations(content, {})
        assert citations == []

    def test_mixed_valid_and_fake_citations(self):
        """Only citations with IDs in citation_map survive; fakes are dropped."""
        content = "[Supplier:s-legit] did well. [Supplier:s-invented] is worse."
        cmap = {"s-legit": "Supplier"}
        citations = extract_citations(content, cmap)
        obj_ids = {c["object_id"] for c in citations}
        assert "s-legit" in obj_ids
        assert "s-invented" not in obj_ids

    def test_multiple_types_only_known_ids_accepted(self):
        """Among multiple citation types, only IDs in citation_map pass."""
        content = "[Supplier:s1][Finding:f1][Risk:r1][ComplianceGap:g1]"
        cmap = {"s1": "Supplier", "r1": "Risk"}  # f1 and g1 are NOT in cmap
        citations = extract_citations(content, cmap)
        obj_ids = {c["object_id"] for c in citations}
        assert "s1" in obj_ids
        assert "r1" in obj_ids
        assert "f1" not in obj_ids
        assert "g1" not in obj_ids

    def test_retrieved_citation_still_requires_cmap(self):
        """Source IDs from cmap that appear in content are still added as 'retrieved'."""
        content = "The supplier s-retrieved is mentioned without brackets."
        cmap = {"s-retrieved": "Supplier"}
        citations = extract_citations(content, cmap)
        assert any(c["object_id"] == "s-retrieved" and c["relevance"] == "retrieved" for c in citations)

    def test_explicit_beats_retrieved_for_same_id(self):
        """When same ID appears bracketed AND in cmap, explicit relevance takes priority."""
        content = "[Supplier:s1] is the primary supplier."
        cmap = {"s1": "Supplier"}
        citations = extract_citations(content, cmap)
        matches = [c for c in citations if c["object_id"] == "s1"]
        assert len(matches) == 1
        assert matches[0]["relevance"] == "explicit"

    def test_valid_citation_type_but_wrong_id_rejected(self):
        """Correct citation type format but ID not in cmap is rejected."""
        content = "[Risk:r-ghost]"
        cmap = {"r-real": "Risk"}
        citations = extract_citations(content, cmap)
        assert not any(c["object_id"] == "r-ghost" for c in citations)

    def test_all_nine_types_accepted_when_in_cmap(self):
        """All 9 citation types are accepted when their IDs exist in citation_map."""
        ids = {
            "s1": "Supplier", "f1": "Finding", "r1": "Risk",
            "rec1": "Recommendation", "e1": "Evidence", "a1": "Assessment",
            "g1": "ComplianceGap", "d1": "Disclosure", "rpt1": "Report",
        }
        content = "[Supplier:s1][Finding:f1][Risk:r1][Recommendation:rec1][Evidence:e1]" \
                  "[Assessment:a1][ComplianceGap:g1][Disclosure:d1][Report:rpt1]"
        citations = extract_citations(content, ids)
        found_types = {c["citation_type"] for c in citations}
        assert len(found_types) == 9

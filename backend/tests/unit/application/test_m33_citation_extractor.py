"""Unit tests for M33 Citation Extractor."""

from __future__ import annotations

from application.copilot.citation_extractor import extract_citations, format_citations_for_prompt


class TestExtractCitations:
    def test_explicit_supplier_citation(self):
        content = "Based on data, [Supplier:s-abc123] is critical."
        cmap = {"s-abc123": "Supplier"}
        citations = extract_citations(content, cmap)
        assert len(citations) == 1
        assert citations[0]["citation_type"] == "Supplier"
        assert citations[0]["object_id"] == "s-abc123"
        assert citations[0]["relevance"] == "explicit"

    def test_explicit_finding_citation(self):
        # Citation only accepted when id is in citation_map (M33.1 hardening)
        content = "See [Finding:f-001] for the child labour finding."
        cmap = {"f-001": "Finding"}
        citations = extract_citations(content, cmap)
        assert any(c["citation_type"] == "Finding" and c["object_id"] == "f-001" for c in citations)

    def test_explicit_finding_citation_not_in_cmap_rejected(self):
        content = "See [Finding:fake-id] for the finding."
        cmap = {}
        citations = extract_citations(content, cmap)
        assert not any(c["object_id"] == "fake-id" for c in citations)

    def test_multiple_citations_extracted(self):
        content = "See [Supplier:s1] and [Risk:r1] and [ComplianceGap:g1]."
        cmap = {"s1": "Supplier", "r1": "Risk", "g1": "ComplianceGap"}
        citations = extract_citations(content, cmap)
        types = {c["citation_type"] for c in citations}
        assert "Supplier" in types
        assert "Risk" in types
        assert "ComplianceGap" in types

    def test_retrieved_citation_from_cmap(self):
        content = "The supplier s-999 has high risk."
        cmap = {"s-999": "Supplier"}
        citations = extract_citations(content, cmap)
        assert any(c["object_id"] == "s-999" and c["relevance"] == "retrieved" for c in citations)

    def test_no_duplicate_when_explicit_and_retrieved(self):
        content = "[Supplier:s1] is mentioned."
        cmap = {"s1": "Supplier"}
        citations = extract_citations(content, cmap)
        # Should appear once — explicit takes priority
        assert len([c for c in citations if c["object_id"] == "s1"]) == 1
        assert citations[0]["relevance"] == "explicit"

    def test_empty_content(self):
        assert extract_citations("", {}) == []

    def test_invalid_citation_type_ignored(self):
        content = "[FakeType:obj1] is here."
        citations = extract_citations(content, {})
        assert not any(c["citation_type"] == "FakeType" for c in citations)

    def test_all_valid_citation_types(self):
        # All 9 types accepted when their IDs are present in citation_map
        cmap = {
            "s1": "Supplier",
            "f1": "Finding",
            "r1": "Risk",
            "rec1": "Recommendation",
            "e1": "Evidence",
            "a1": "Assessment",
            "g1": "ComplianceGap",
            "d1": "Disclosure",
            "rpt1": "Report",
        }
        content = " ".join(
            [
                "[Supplier:s1]",
                "[Finding:f1]",
                "[Risk:r1]",
                "[Recommendation:rec1]",
                "[Evidence:e1]",
                "[Assessment:a1]",
                "[ComplianceGap:g1]",
                "[Disclosure:d1]",
                "[Report:rpt1]",
            ]
        )
        citations = extract_citations(content, cmap)
        types = {c["citation_type"] for c in citations}
        assert len(types) == 9


class TestFormatCitationsForPrompt:
    def test_empty_map_returns_empty(self):
        assert format_citations_for_prompt({}) == ""

    def test_includes_citation_types(self):
        cmap = {"s1": "Supplier", "f1": "Finding"}
        result = format_citations_for_prompt(cmap)
        assert "[Supplier:s1]" in result
        assert "[Finding:f1]" in result

    def test_caps_at_50_entries(self):
        cmap = {f"s{i}": "Supplier" for i in range(100)}
        result = format_citations_for_prompt(cmap)
        assert result.count("[Supplier:") <= 50

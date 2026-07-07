"""Unit tests for M33 Context Assembler."""

from __future__ import annotations

from application.copilot.context_assembler import assemble_context, build_citation_map
from application.copilot.retrieval.base import RetrievalResult


def _result(
    retriever: str, data: list, source_ids: list, citation_type: str = "Supplier"
) -> RetrievalResult:
    return RetrievalResult(
        retriever=retriever,
        provenance=f"Retrieved {len(data)} {citation_type}s",
        data=data,
        source_ids=source_ids,
        citation_type=citation_type,
    )


class TestAssembleContext:
    def test_empty_results_returns_fallback(self):
        ctx = assemble_context([])
        assert "No relevant data" in ctx

    def test_single_result_contains_provenance(self):
        r = _result("supplier_retriever", [{"name": "ACME"}], ["s1"])
        ctx = assemble_context([r])
        assert "supplier_retriever" in ctx.upper() or "SUPPLIER_RETRIEVER" in ctx
        assert "ACME" in ctx

    def test_multiple_results_separated(self):
        r1 = _result("supplier_retriever", [{"id": "s1"}], ["s1"])
        r2 = _result("compliance_retriever", [{"id": "g1"}], ["g1"], citation_type="ComplianceGap")
        ctx = assemble_context([r1, r2])
        assert "s1" in ctx
        assert "g1" in ctx

    def test_section_included_whole_or_not_at_all(self):
        # M33.2: sections are included whole or skipped (no mid-string truncation).
        # A section that fits within max_chars is fully included.
        small_data = [{"id": "s1"}]
        r = _result("retriever", small_data, ["s1"])
        ctx = assemble_context([r], max_chars=500)
        assert "s1" in ctx  # section was included intact

    def test_oversized_single_section_returns_no_context(self):
        # M33.2: if even the first section is too large, no partial data leaks — returns no-context msg.
        big_data = [{"text": "x" * 1000}] * 20
        r = _result("retriever", big_data, ["s1"])
        ctx = assemble_context([r], max_chars=100)
        assert "No relevant data" in ctx

    def test_empty_data_list_skipped(self):
        r = _result("retriever", [], ["s1"])
        ctx = assemble_context([r])
        assert "No relevant data" in ctx


class TestBuildCitationMap:
    def test_maps_source_ids_to_citation_types(self):
        r1 = _result("supplier_retriever", [], ["s1", "s2"], citation_type="Supplier")
        r2 = _result("compliance_retriever", [], ["g1"], citation_type="ComplianceGap")
        cmap = build_citation_map([r1, r2])
        assert cmap["s1"] == "Supplier"
        assert cmap["s2"] == "Supplier"
        assert cmap["g1"] == "ComplianceGap"

    def test_empty_results_returns_empty_map(self):
        assert build_citation_map([]) == {}

    def test_later_retriever_overwrites_same_id(self):
        r1 = _result("r1", [], ["shared-id"], citation_type="Supplier")
        r2 = _result("r2", [], ["shared-id"], citation_type="Finding")
        cmap = build_citation_map([r1, r2])
        assert cmap["shared-id"] == "Finding"

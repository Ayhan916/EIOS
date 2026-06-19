"""M33.2 — Context Budget Management Tests.

Verifies section-level budget tracking: complete sections included or skipped,
correct inclusion/omission tracking, and budget note generation.
"""

from __future__ import annotations

from application.copilot.context_assembler import (
    NO_CONTEXT_MSG,
    assemble_context_with_budget,
)
from application.copilot.context_budget import (
    ContextBudget,
    budget_dict,
    format_budget_note,
)
from application.copilot.retrieval.base import RetrievalResult


def _result(retriever: str, data_size: int = 5) -> RetrievalResult:
    return RetrievalResult(
        retriever=retriever,
        provenance=f"{retriever} Intelligence",
        data=[{"id": f"{retriever}-{i}", "value": "x" * 20} for i in range(data_size)],
        source_ids=[f"{retriever}-{i}" for i in range(data_size)],
        citation_type="Supplier",
    )


def _empty_result(retriever: str) -> RetrievalResult:
    return RetrievalResult(
        retriever=retriever,
        provenance=f"{retriever} Intelligence",
        data=[],
        source_ids=[],
        citation_type="",
    )


class TestContextBudgetTracking:
    def test_empty_results_returns_no_context_msg(self):
        context, budget = assemble_context_with_budget([])
        assert context == NO_CONTEXT_MSG
        assert budget.used_chars == 0
        assert not budget.truncated

    def test_single_result_included(self):
        result = _result("supplier_retriever", data_size=2)
        context, budget = assemble_context_with_budget([result])
        assert "supplier_retriever" in budget.retrievers_included
        assert budget.retrievers_included == ["supplier_retriever"]
        assert budget.truncated is False

    def test_empty_retriever_tracked(self):
        result = _empty_result("supplier_retriever")
        context, budget = assemble_context_with_budget([result])
        assert "supplier_retriever" in budget.retrievers_empty
        assert "supplier_retriever" not in budget.retrievers_included

    def test_overflow_section_omitted(self):
        # First section is small enough to fit; second is too large
        small = RetrievalResult(
            retriever="supplier_retriever",
            provenance="Supplier Intelligence",
            data=[{"id": "s1"}],
            source_ids=["s1"],
            citation_type="Supplier",
        )
        big = _result("compliance_retriever", data_size=200)
        context, budget = assemble_context_with_budget([small, big], max_chars=200)
        # supplier included (small), compliance omitted (big)
        assert budget.truncated is True
        assert "compliance_retriever" in budget.retrievers_omitted

    def test_no_partial_json_in_context(self):
        results = [
            _result("supplier_retriever", data_size=50),
            _result("compliance_retriever", data_size=50),
        ]
        context, budget = assemble_context_with_budget(results, max_chars=300)
        if budget.truncated:
            assert context.count("{") == context.count("}")

    def test_used_chars_matches_context_length(self):
        result = _result("supplier_retriever", data_size=3)
        context, budget = assemble_context_with_budget([result])
        assert budget.used_chars == len(context)

    def test_all_sections_fit_within_max_chars(self):
        results = [_result("supplier_retriever", data_size=2)]
        context, budget = assemble_context_with_budget(results, max_chars=10_000)
        assert budget.used_chars <= 10_000
        assert budget.truncated is False

    def test_multiple_empty_retrievers_all_tracked(self):
        results = [
            _empty_result("supplier_retriever"),
            _empty_result("compliance_retriever"),
        ]
        context, budget = assemble_context_with_budget(results)
        assert "supplier_retriever" in budget.retrievers_empty
        assert "compliance_retriever" in budget.retrievers_empty
        assert context == NO_CONTEXT_MSG


class TestFormatBudgetNote:
    def test_no_note_when_not_truncated(self):
        budget = ContextBudget(max_chars=8000, truncated=False)
        assert format_budget_note(budget) == ""

    def test_no_note_when_truncated_but_nothing_omitted(self):
        budget = ContextBudget(max_chars=8000, truncated=True, retrievers_omitted=[])
        assert format_budget_note(budget) == ""

    def test_note_includes_omitted_retriever_label(self):
        budget = ContextBudget(
            max_chars=8000,
            truncated=True,
            retrievers_omitted=["compliance_retriever", "disclosure_retriever"],
        )
        note = format_budget_note(budget)
        assert "CONTEXT LIMIT NOTE" in note
        assert "compliance" in note
        assert "disclosure" in note

    def test_note_strips_underscore_retriever_suffix(self):
        budget = ContextBudget(
            max_chars=8000,
            truncated=True,
            retrievers_omitted=["due_diligence_retriever"],
        )
        note = format_budget_note(budget)
        assert "_retriever" not in note
        assert "due diligence" in note


class TestBudgetDict:
    def test_all_keys_present(self):
        budget = ContextBudget(
            max_chars=8000,
            used_chars=4000,
            truncated=False,
            retrievers_included=["supplier_retriever"],
            retrievers_omitted=[],
            retrievers_empty=["compliance_retriever"],
        )
        d = budget_dict(budget)
        assert d["max_chars"] == 8000
        assert d["used_chars"] == 4000
        assert d["truncated"] is False
        assert d["retrievers_included"] == ["supplier_retriever"]
        assert d["retrievers_omitted"] == []
        assert d["retrievers_empty"] == ["compliance_retriever"]

    def test_budget_dict_serializable(self):
        import json
        budget = ContextBudget(max_chars=8000)
        d = budget_dict(budget)
        assert isinstance(json.dumps(d), str)

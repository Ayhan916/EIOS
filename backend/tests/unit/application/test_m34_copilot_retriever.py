"""M34 Copilot external intelligence retriever tests."""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock


def _now():
    return datetime.now(UTC)


def _make_enrichment_model(supplier_id, org_id):
    m = MagicMock()
    m.id = f"enr-{supplier_id}"
    m.supplier_id = supplier_id
    m.organization_id = org_id
    m.country_code = "CN"
    m.country_risk_level = "high"
    m.country_risk_score = 70.0
    m.sanctions_exposure = "none"
    m.sector_percentile = 45.0
    m.percentile_rank = "median"
    m.benchmark_score = 60.0
    m.benchmark_explanation = "Supplier is below median."
    m.external_risk_score = 35.0
    m.combined_risk_score = 42.0
    m.active_signal_count = 1
    m.dataset_version = "2025-Q1"
    m.enriched_at = _now()
    return m


def _make_signal_model(supplier_id, org_id):
    m = MagicMock()
    m.id = f"sig-{supplier_id}"
    m.signal_type = "sanctions"
    m.severity = "high"
    m.description = "OFAC match"
    m.country_code = "RU"
    m.supplier_id = supplier_id
    m.source_name = "ofac"
    m.source_version = "2025"
    m.observed_at = _now()
    return m


def _make_session_with_two_results(enrichments, signals):
    session = AsyncMock()

    enrich_result = MagicMock()
    enrich_result.scalars.return_value.all.return_value = enrichments

    signal_result = MagicMock()
    signal_result.scalars.return_value.all.return_value = signals

    session.execute = AsyncMock(side_effect=[enrich_result, signal_result])
    return session


@pytest.mark.asyncio
async def test_retriever_returns_retrieval_result():
    enrich = _make_enrichment_model("sup-001", "org-001")
    signal = _make_signal_model("sup-001", "org-001")
    session = _make_session_with_two_results([enrich], [signal])

    from application.copilot.retrieval.external_intelligence_retriever import (
        retrieve_external_intelligence_context,
    )
    result = await retrieve_external_intelligence_context("org-001", session)
    assert result.retriever == "external_intelligence_retriever"


@pytest.mark.asyncio
async def test_retriever_includes_enrichment_data():
    enrich = _make_enrichment_model("sup-001", "org-001")
    session = _make_session_with_two_results([enrich], [])

    from application.copilot.retrieval.external_intelligence_retriever import (
        retrieve_external_intelligence_context,
    )
    result = await retrieve_external_intelligence_context("org-001", session)
    assert any(d.get("supplier_id") == "sup-001" for d in result.data)


@pytest.mark.asyncio
async def test_retriever_includes_signal_data():
    signal = _make_signal_model("sup-001", "org-001")
    session = _make_session_with_two_results([], [signal])

    from application.copilot.retrieval.external_intelligence_retriever import (
        retrieve_external_intelligence_context,
    )
    result = await retrieve_external_intelligence_context("org-001", session)
    assert any(d.get("signal_id") is not None for d in result.data)


@pytest.mark.asyncio
async def test_retriever_includes_freshness_metadata():
    enrich = _make_enrichment_model("sup-001", "org-001")
    session = _make_session_with_two_results([enrich], [])

    from application.copilot.retrieval.external_intelligence_retriever import (
        retrieve_external_intelligence_context,
    )
    result = await retrieve_external_intelligence_context("org-001", session)
    assert len(result.freshness_metadata) >= 1
    assert "object_type" in result.freshness_metadata[0]
    assert result.freshness_metadata[0]["object_type"] == "SupplierEnrichment"


@pytest.mark.asyncio
async def test_retriever_provenance_includes_counts():
    enrich = _make_enrichment_model("sup-001", "org-001")
    signal = _make_signal_model("sup-001", "org-001")
    session = _make_session_with_two_results([enrich], [signal])

    from application.copilot.retrieval.external_intelligence_retriever import (
        retrieve_external_intelligence_context,
    )
    result = await retrieve_external_intelligence_context("org-001", session)
    assert "1" in result.provenance
    assert "enrichment" in result.provenance.lower()


@pytest.mark.asyncio
async def test_retriever_empty_org_returns_empty_data():
    session = _make_session_with_two_results([], [])

    from application.copilot.retrieval.external_intelligence_retriever import (
        retrieve_external_intelligence_context,
    )
    result = await retrieve_external_intelligence_context("org-empty", session)
    assert result.data == []
    assert result.source_ids == []


@pytest.mark.asyncio
async def test_retriever_supplier_filter():
    enrich1 = _make_enrichment_model("sup-001", "org-001")
    enrich2 = _make_enrichment_model("sup-002", "org-001")
    # With supplier filter, only sup-001 should be in session call
    # The query is built with WHERE supplier_id = supplier_id
    session = _make_session_with_two_results([enrich1], [])

    from application.copilot.retrieval.external_intelligence_retriever import (
        retrieve_external_intelligence_context,
    )
    result = await retrieve_external_intelligence_context(
        "org-001", session, supplier_id="sup-001"
    )
    # Result comes from mocked DB — just ensure no crash and correct retriever
    assert result.retriever == "external_intelligence_retriever"


@pytest.mark.asyncio
async def test_retriever_citation_type_is_supplier():
    session = _make_session_with_two_results([], [])

    from application.copilot.retrieval.external_intelligence_retriever import (
        retrieve_external_intelligence_context,
    )
    result = await retrieve_external_intelligence_context("org-001", session)
    assert result.citation_type == "Supplier"

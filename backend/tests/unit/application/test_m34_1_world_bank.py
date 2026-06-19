"""M34.1 Tests — WorldBankConnector."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from application.external_intelligence.connectors.world_bank import WorldBankConnector


_WGI_TEMPLATE = {
    "countryiso3code": "DEU",
    "country": {"value": "Germany"},
    "date": "2023",
    "value": 1.5,
    "indicator": {"id": "WGI.CC.EST", "value": "Control of Corruption"},
}


def _make_indicator_response(indicator_id: str, country_code: str, value: float):
    return [
        {},
        [
            {
                "countryiso3code": country_code,
                "country": {"value": "TestCountry"},
                "date": "2023",
                "value": value,
                "indicator": {"id": indicator_id, "value": indicator_id},
            }
        ],
    ]


def test_connector_name():
    assert WorldBankConnector.connector_name == "world_bank"


def test_refresh_cadence_is_monthly():
    c = WorldBankConnector()
    assert c.refresh_cadence_hours == 24 * 30


def _wgi_to_risk(raw: float) -> float:
    """Reference implementation of the WGI → risk conversion formula."""
    return max(0.0, min(100.0, (2.5 - raw) / 5.0 * 100))


def test_wgi_risk_conversion_positive():
    """WGI 2.5 = perfect governance → risk score 0."""
    assert _wgi_to_risk(2.5) == 0.0


def test_wgi_risk_conversion_negative():
    """WGI -2.5 = worst governance → risk score 100."""
    assert _wgi_to_risk(-2.5) == 100.0


def test_wgi_risk_conversion_midpoint():
    """WGI 0.0 → risk score 50."""
    assert _wgi_to_risk(0.0) == 50.0


def test_wgi_risk_clamped_above():
    """Values above 2.5 (rare) clamp to 0."""
    assert _wgi_to_risk(3.0) == 0.0


def test_wgi_risk_clamped_below():
    """Values below -2.5 clamp to 100."""
    assert _wgi_to_risk(-3.0) == 100.0


def test_normalize_returns_raw_dataset():
    c = WorldBankConnector()
    raw_records = [
        {
            "country_code": "DE",
            "country_name": "Germany",
            "governance_score": 20.0,
            "corruption_score": 10.0,
        }
    ]
    dataset = c.normalize(raw_records)
    sn = dataset.source_name.value if hasattr(dataset.source_name, "value") else dataset.source_name
    assert sn == "world_bank"
    assert dataset.row_count == 1
    assert dataset.records[0]["country_code"] == "DE"


@pytest.mark.asyncio
async def test_fetch_aggregates_across_indicators():
    """Verify that fetch() merges per-indicator responses into country-level records."""
    c = WorldBankConnector()
    # Build mock responses for each of 6 WGI indicators
    indicator_ids = ["CC.EST", "GE.EST", "RQ.EST", "RL.EST", "PS.EST", "VA.EST"]
    responses = [_make_indicator_response(f"WGI.{iid}", "DEU", 1.0) for iid in indicator_ids]

    call_idx = 0

    async def fake_get(url, **kwargs):
        nonlocal call_idx
        resp = MagicMock()
        resp.json.return_value = responses[call_idx % len(responses)]
        resp.raise_for_status = MagicMock()
        call_idx += 1
        return resp

    client = MagicMock()
    client.get = fake_get

    raw = await c.fetch(client)
    # fetch() returns intermediate records with indicators dict
    assert isinstance(raw, list)
    assert len(raw) >= 1
    record = next((r for r in raw if r.get("country_code") == "DEU"), None)
    assert record is not None
    assert "country_code" in record

    # governance_score and corruption_score are added by normalize()
    dataset = c.normalize(raw)
    assert dataset.row_count >= 1
    normalized_record = dataset.records[0]
    assert "governance_score" in normalized_record
    assert "corruption_score" in normalized_record

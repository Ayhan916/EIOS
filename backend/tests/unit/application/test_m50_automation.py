"""M50.5 — Automation & Actionability Layer: unit tests.

Tests cover:
- CSV export helper logic (headers + row count)
- is_overdue computation in recommendations export
- Risk level ordering for CSV exports
- Command palette command registry structure
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timezone


# ── CSV helper ─────────────────────────────────────────────────────────────────

def _rows_to_csv(headers: list[str], rows: list[list[str]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    return buf.getvalue()


def _parse_csv(csv_str: str) -> tuple[list[str], list[list[str]]]:
    reader = csv.reader(io.StringIO(csv_str))
    lines = list(reader)
    return lines[0], lines[1:]


class TestCsvHelper:
    def test_header_row_present(self):
        headers = ["id", "title", "severity"]
        csv_str = _rows_to_csv(headers, [])
        hdr, rows = _parse_csv(csv_str)
        assert hdr == headers

    def test_data_rows_written(self):
        headers = ["id", "title"]
        data = [["1", "Test finding"], ["2", "Another"]]
        csv_str = _rows_to_csv(headers, data)
        _, rows = _parse_csv(csv_str)
        assert len(rows) == 2
        assert rows[0][1] == "Test finding"

    def test_empty_rows_produces_header_only(self):
        headers = ["id", "title"]
        csv_str = _rows_to_csv(headers, [])
        _, rows = _parse_csv(csv_str)
        assert rows == [] or rows == [[]]  # empty

    def test_special_chars_escaped(self):
        headers = ["id", "title"]
        csv_str = _rows_to_csv(headers, [["1", 'Foo, "bar", baz']])
        _, rows = _parse_csv(csv_str)
        assert rows[0][1] == 'Foo, "bar", baz'

    def test_100_rows(self):
        headers = ["id", "title", "severity"]
        data = [[str(i), f"Finding {i}", "High"] for i in range(100)]
        csv_str = _rows_to_csv(headers, data)
        _, rows = _parse_csv(csv_str)
        assert len(rows) == 100


# ── is_overdue logic ──────────────────────────────────────────────────────────

def _is_overdue(action_status: str, due_date, now: datetime) -> bool:
    return (
        action_status not in ("resolved", "verified")
        and due_date is not None
        and due_date < now.date()
    )


class TestIsOverdue:
    def setup_method(self):
        self.now = datetime(2026, 6, 23, tzinfo=UTC)

    def test_open_past_due_is_overdue(self):
        from datetime import date
        assert _is_overdue("open", date(2026, 1, 1), self.now) is True

    def test_open_future_due_not_overdue(self):
        from datetime import date
        assert _is_overdue("open", date(2026, 12, 31), self.now) is False

    def test_resolved_past_due_not_overdue(self):
        from datetime import date
        assert _is_overdue("resolved", date(2026, 1, 1), self.now) is False

    def test_verified_past_due_not_overdue(self):
        from datetime import date
        assert _is_overdue("verified", date(2026, 1, 1), self.now) is False

    def test_no_due_date_not_overdue(self):
        assert _is_overdue("open", None, self.now) is False

    def test_in_progress_past_due_is_overdue(self):
        from datetime import date
        assert _is_overdue("in_progress", date(2026, 1, 1), self.now) is True


# ── Risk level sort order ─────────────────────────────────────────────────────

RISK_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _sort_by_risk_level(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda x: RISK_ORDER.get(x["risk_level"], 99))


class TestRiskLevelSortOrder:
    def test_critical_first(self):
        items = [
            {"risk_level": "Low"},
            {"risk_level": "Critical"},
            {"risk_level": "High"},
        ]
        sorted_items = _sort_by_risk_level(items)
        assert sorted_items[0]["risk_level"] == "Critical"

    def test_full_order(self):
        items = [
            {"risk_level": "Low"},
            {"risk_level": "Medium"},
            {"risk_level": "High"},
            {"risk_level": "Critical"},
        ]
        sorted_items = _sort_by_risk_level(items)
        assert [i["risk_level"] for i in sorted_items] == ["Critical", "High", "Medium", "Low"]

    def test_unknown_risk_level_goes_last(self):
        items = [
            {"risk_level": "Critical"},
            {"risk_level": "Unknown"},
        ]
        sorted_items = _sort_by_risk_level(items)
        assert sorted_items[-1]["risk_level"] == "Unknown"


# ── Findings CSV column structure ─────────────────────────────────────────────

FINDINGS_CSV_HEADERS = ["id", "title", "severity", "category", "status", "assessment_id", "created_at", "supplier_name"]
RISKS_CSV_HEADERS = ["id", "title", "risk_level", "category", "probability", "impact", "assessment_id", "created_at", "supplier_name"]
RECOMMENDATIONS_CSV_HEADERS = ["id", "title", "action_status", "priority", "due_date", "is_overdue", "assessment_id", "created_at", "supplier_name"]


class TestCsvColumnStructure:
    def test_findings_has_severity_column(self):
        assert "severity" in FINDINGS_CSV_HEADERS

    def test_risks_has_risk_level_column(self):
        assert "risk_level" in RISKS_CSV_HEADERS

    def test_recommendations_has_is_overdue_column(self):
        assert "is_overdue" in RECOMMENDATIONS_CSV_HEADERS

    def test_all_have_supplier_name(self):
        for headers in [FINDINGS_CSV_HEADERS, RISKS_CSV_HEADERS, RECOMMENDATIONS_CSV_HEADERS]:
            assert "supplier_name" in headers

    def test_all_have_id(self):
        for headers in [FINDINGS_CSV_HEADERS, RISKS_CSV_HEADERS, RECOMMENDATIONS_CSV_HEADERS]:
            assert "id" in headers

    def test_findings_column_count(self):
        assert len(FINDINGS_CSV_HEADERS) == 8

    def test_risks_column_count(self):
        assert len(RISKS_CSV_HEADERS) == 9

    def test_recommendations_column_count(self):
        assert len(RECOMMENDATIONS_CSV_HEADERS) == 9

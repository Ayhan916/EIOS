"""
M29 Board Report PDF Renderer

Produces executive-ready board reports from the frozen report_data snapshot.
Reproducible: same snapshot → identical PDF byte-for-byte (modulo font rendering).

Uses the same _EIOSReport base class and latin-1 safe text handling as the
assessment pdf_renderer.  All colour constants are shared via the same palette.
"""

from __future__ import annotations

from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ── Colour palette (shared with assessment renderer) ──────────────────────────
_DARK = (30, 40, 55)
_MID = (80, 95, 110)
_LIGHT = (245, 247, 249)
_ACCENT = (15, 98, 179)
_WHITE = (255, 255, 255)
_GREEN = (40, 130, 60)
_AMBER = (180, 130, 0)
_RED = (180, 30, 30)

_BAND_COLOURS: dict[str, tuple[int, int, int]] = {
    "Critical": (180, 30, 30),
    "High": (210, 80, 0),
    "Moderate": (180, 130, 0),
    "Low": (40, 130, 60),
}

_UNICODE_MAP = str.maketrans(
    {
        "—": " - ", "–": "-", "‘": "'", "’": "'",
        "“": '"', "”": '"', "…": "...", "•": "*",
        " ": " ", "→": "->",
    }
)


def _latin1(text: str) -> str:
    return text.translate(_UNICODE_MAP).encode("latin-1", errors="replace").decode("latin-1")


def _safe(val: Any, max_chars: int = 200) -> str:
    s = str(val or "-")
    return _latin1(s[:max_chars] + ("..." if len(s) > max_chars else ""))


# ── PDF class ─────────────────────────────────────────────────────────────────


class _BoardReport(FPDF):
    def __init__(self, title: str, org: str, generated_at: str, report_id: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._title = _latin1(title)
        self._org = _latin1(org)
        self._generated_at = _latin1(generated_at)
        self._report_id = _latin1(report_id)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=18, top=15, right=18)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_MID)
        self.cell(0, 6, f"EIOS Board Report  |  {self._org}", align="L")
        self.set_x(-70)
        self.cell(0, 6, self._title[:45], align="R")
        self.ln(1)
        self.set_draw_color(*_MID)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_draw_color(*_MID)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_MID)
        self.cell(0, 5, f"Generated {self._generated_at}  |  Report ID: {self._report_id}", align="L")
        self.cell(0, 5, f"Page {self.page_no()}", align="R")

    def _section(self, text: str) -> None:
        self.set_fill_color(*_ACCENT)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, f"  {_latin1(text)}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.set_text_color(*_DARK)

    def _subsection(self, text: str) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_MID)
        self.cell(0, 6, _latin1(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_DARK)

    def _body(self, text: str) -> None:
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_DARK)
        self.multi_cell(0, 5, _latin1(text))

    def _kv(self, key: str, val: str) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_MID)
        self.cell(55, 5, _latin1(key) + ":", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_DARK)
        self.multi_cell(0, 5, _latin1(val))

    def _stat_block(self, stats: list[tuple[str, str, tuple[int, int, int]]]) -> None:
        """Render a row of coloured stat boxes."""
        usable = self.w - self.l_margin - self.r_margin
        col_w = usable / len(stats)
        for _label, value, colour in stats:
            self.set_fill_color(*colour)
            self.set_text_color(*_WHITE)
            self.set_font("Helvetica", "B", 18)
            self.cell(col_w, 14, _safe(value, 10), fill=True, align="C")
        self.ln()
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "", 8)
        for label, _, _ in stats:
            self.cell(col_w, 6, _latin1(label), fill=True, align="C")
        self.ln(6)
        self.set_fill_color(*_WHITE)
        self.set_text_color(*_DARK)

    def _table_header(self, cols: list[tuple[str, float]]) -> None:
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 8)
        for label, w in cols:
            self.cell(w, 6, _latin1(label), border=0, fill=True, align="C")
        self.ln()
        self.set_text_color(*_DARK)
        self.set_fill_color(*_LIGHT)

    def _row_bg(self, i: int) -> None:
        self.set_fill_color(*(_WHITE if i % 2 == 0 else _LIGHT))


# ── Public API ────────────────────────────────────────────────────────────────


def render_board_report_pdf(
    report_data: dict[str, Any],
    report_id: str,
    organization_name: str,
) -> bytes:
    """Render a board report PDF from the frozen report_data snapshot."""
    meta = report_data.get("meta", {})
    title = meta.get("title", "Board Report")
    generated_at = meta.get("generated_at", "")
    period = f"{meta.get('period_start', '')} to {meta.get('period_end', '')}"

    pdf = _BoardReport(
        title=title,
        org=organization_name,
        generated_at=generated_at,
        report_id=report_id,
    )

    _cover(pdf, meta, period, organization_name)
    _exec_summary_section(pdf, report_data)
    _portfolio_health(pdf, report_data)
    _risk_overview(pdf, report_data)
    _top_high_risk(pdf, report_data)
    _top_deteriorating(pdf, report_data)
    _critical_findings(pdf, report_data)
    _overdue_actions(pdf, report_data)
    _governance_metrics(pdf, report_data)
    _action_effectiveness(pdf, report_data)
    _kpi_trends(pdf, report_data)
    _appendix(pdf, meta, report_id)

    return bytes(pdf.output())


# ── Sections ──────────────────────────────────────────────────────────────────


def _cover(pdf: _BoardReport, meta: dict, period: str, org: str) -> None:
    pdf.add_page()
    pdf.set_fill_color(*_ACCENT)
    pdf.rect(0, 0, 210, 60, "F")

    pdf.set_y(18)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*_WHITE)
    pdf.cell(0, 10, "Board & Executive Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "ESG Supplier Intelligence  |  EIOS Platform", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(75)
    pdf.set_text_color(*_DARK)
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _safe(meta.get("title", "Board Report"), 120), align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_MID)
    for label, val in [
        ("Organization", org),
        ("Period", period),
        ("Generated", meta.get("generated_at", "-")),
        ("Report ID", meta.get("report_id", "-")),
        ("Version", meta.get("report_version", "1.0")),
    ]:
        pdf._kv(label, str(val))
        pdf.ln(1)

    pdf.ln(10)
    pdf.set_draw_color(*_ACCENT)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    # Confidentiality banner
    pdf.set_fill_color(255, 243, 205)
    pdf.set_draw_color(200, 160, 0)
    pdf.set_line_width(0.3)
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.w - pdf.l_margin - pdf.r_margin, 14, "FD")
    pdf.set_y(pdf.get_y() + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.cell(0, 4, "CONFIDENTIAL - BOARD USE ONLY", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(0, 4, "This document contains commercially sensitive ESG intelligence. "
             "Do not distribute without board authorisation.", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*_DARK)


def _exec_summary_section(pdf: _BoardReport, data: dict) -> None:
    pdf.add_page()
    pdf._section("Executive Summary")
    summary = data.get("executive_summary", "")
    if summary:
        pdf._body(summary)
    else:
        pdf._body("Executive summary not available.")
    pdf.ln(4)


def _portfolio_health(pdf: _BoardReport, data: dict) -> None:
    ps = data.get("portfolio_summary", {})
    if not ps:
        return
    pdf._section("Portfolio Health")

    pdf._stat_block([
        ("Total Suppliers", str(ps.get("total_suppliers", 0)), _ACCENT),
        ("Scored", str(ps.get("scored_suppliers", 0)), _MID),
        ("Critical Risk", str(ps.get("critical_risk_suppliers", 0)), _RED),
        ("High Risk", str(ps.get("high_risk_suppliers", 0)), (210, 80, 0)),
        ("Deteriorating", str(ps.get("deteriorating_suppliers", 0)), _AMBER),
        ("Improving", str(ps.get("improving_suppliers", 0)), _GREEN),
    ])

    if ps.get("avg_esg_score") is not None:
        pdf._kv("Average ESG Score", f"{ps['avg_esg_score']:.1f} / 100")
        pdf.ln(1)
    if ps.get("avg_risk_score") is not None:
        pdf._kv("Average Risk Score", f"{ps['avg_risk_score']:.1f} / 100")
        pdf.ln(1)
    pdf.ln(3)


def _risk_overview(pdf: _BoardReport, data: dict) -> None:
    ps = data.get("portfolio_summary", {})
    dist = ps.get("risk_distribution", {})
    if not dist:
        return

    pdf._section("Risk Score Distribution")
    total = sum(dist.values()) or 1
    usable = pdf.w - pdf.l_margin - pdf.r_margin

    for band in ("Critical", "High", "Moderate", "Low"):
        count = dist.get(band, 0)
        pct = count / total
        colour = _BAND_COLOURS.get(band, _MID)
        bar_w = max(2.0, usable * 0.55 * pct)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_DARK)
        pdf.cell(25, 7, _latin1(band))
        pdf.set_fill_color(*colour)
        pdf.cell(bar_w, 7, "", fill=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(10, 7, f"  {count}")
        pdf.ln()

    pdf.ln(3)

    # Action overview
    act = data.get("action_summary", {})
    if act:
        pdf._subsection("Action Overview")
        pdf._kv("Open Actions", str(act.get("open_actions", 0)))
        pdf.ln(1)
        pdf._kv("Overdue Actions", str(act.get("overdue_actions", 0)))
        pdf.ln(1)
        if act.get("resolution_rate") is not None:
            pdf._kv("Resolution Rate", f"{act['resolution_rate'] * 100:.1f}%")
            pdf.ln(1)
        pdf.ln(3)


def _top_high_risk(pdf: _BoardReport, data: dict) -> None:
    suppliers = data.get("top_high_risk_suppliers", [])
    if not suppliers:
        return
    pdf.add_page()
    pdf._section(f"Top High-Risk Suppliers  ({len(suppliers)})")

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("Rank", 12), ("Supplier", usable - 12 - 22 - 28 - 22 - 30),
        ("Band", 22), ("Risk Score", 28), ("Trend", 22), ("Country", 30),
    ]
    pdf._table_header(cols)

    for i, s in enumerate(suppliers):
        pdf._row_bg(i)
        band = s.get("risk_band", "Low")
        colour = _BAND_COLOURS.get(band, _MID)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        pdf.cell(cols[0][1], 6, str(i + 1), fill=True, align="C")
        pdf.cell(cols[1][1], 6, _safe(s.get("supplier_name", ""), 35), fill=True)
        pdf.set_fill_color(*colour)
        pdf.set_text_color(*_WHITE)
        pdf.cell(cols[2][1], 6, _latin1(band), fill=True, align="C")
        pdf._row_bg(i)
        pdf.set_text_color(*_DARK)
        pdf.cell(cols[3][1], 6, f"{s.get('risk_score', 0):.1f}", fill=True, align="C")
        trend = s.get("trend", "Stable")
        trend_col = _GREEN if trend == "Improving" else (_RED if trend == "Deteriorating" else _MID)
        pdf.set_text_color(*trend_col)
        pdf.cell(cols[4][1], 6, _latin1(trend), fill=True, align="C")
        pdf.set_text_color(*_DARK)
        pdf.cell(cols[5][1], 6, _safe(s.get("country", ""), 15), fill=True, align="C")
        pdf.ln()

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)
    pdf.ln(4)


def _top_deteriorating(pdf: _BoardReport, data: dict) -> None:
    suppliers = data.get("top_deteriorating_suppliers", [])
    if not suppliers:
        return

    pdf._section(f"Deteriorating Suppliers  ({len(suppliers)})")
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("Supplier", usable - 22 - 22 - 28),
        ("Trend Delta", 22), ("Band", 22), ("Risk Score", 28),
    ]
    pdf._table_header(cols)

    for i, s in enumerate(suppliers):
        pdf._row_bg(i)
        band = s.get("risk_band", "Low")
        colour = _BAND_COLOURS.get(band, _MID)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        pdf.cell(cols[0][1], 6, _safe(s.get("supplier_name", ""), 40), fill=True)
        delta = s.get("trend_delta", 0.0)
        pdf.set_text_color(*_RED)
        pdf.cell(cols[1][1], 6, f"{delta:+.1f}", fill=True, align="C")
        pdf.set_fill_color(*colour)
        pdf.set_text_color(*_WHITE)
        pdf.cell(cols[2][1], 6, _latin1(band), fill=True, align="C")
        pdf._row_bg(i)
        pdf.set_text_color(*_DARK)
        pdf.cell(cols[3][1], 6, f"{s.get('risk_score', 0):.1f}", fill=True, align="C")
        pdf.ln()

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)
    pdf.ln(4)


def _critical_findings(pdf: _BoardReport, data: dict) -> None:
    items = data.get("critical_findings_summary", [])
    if not items:
        return

    pdf.add_page()
    pdf._section(f"Critical Findings Summary  ({len(items)})")
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("Supplier", usable * 0.30), ("Finding", usable * 0.45),
        ("Pillar", usable * 0.12), ("Category", usable * 0.13),
    ]
    pdf._table_header(cols)

    for i, item in enumerate(items):
        pdf._row_bg(i)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        y_start = pdf.get_y()
        pdf.multi_cell(cols[0][1], 5, _safe(item.get("supplier_name", ""), 30), fill=True)
        y_end = pdf.get_y()
        row_h = max(6.0, y_end - y_start)
        pdf.set_xy(pdf.l_margin + cols[0][1], y_start)
        pdf.cell(cols[1][1], row_h, _safe(item.get("title", ""), 55), fill=True)
        pdf.cell(cols[2][1], row_h, _safe(item.get("pillar", ""), 12), fill=True, align="C")
        pdf.cell(cols[3][1], row_h, _safe(item.get("category", ""), 15), fill=True, align="C")
        pdf.set_xy(pdf.l_margin, y_end)

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)
    pdf.ln(4)


def _overdue_actions(pdf: _BoardReport, data: dict) -> None:
    items = data.get("overdue_actions_summary", [])
    if not items:
        return

    pdf._section(f"Overdue Actions  ({len(items)})")
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("Supplier", usable * 0.28), ("Action", usable * 0.40),
        ("Due Date", usable * 0.15), ("Days Overdue", usable * 0.17),
    ]
    pdf._table_header(cols)

    for i, item in enumerate(items):
        pdf._row_bg(i)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        pdf.cell(cols[0][1], 6, _safe(item.get("supplier_name", ""), 30), fill=True)
        pdf.cell(cols[1][1], 6, _safe(item.get("title", ""), 50), fill=True)
        pdf.cell(cols[2][1], 6, _safe(str(item.get("due_date", "-"))[:10], 15), fill=True, align="C")
        days = item.get("days_overdue", 0)
        pdf.set_text_color(*(_RED if days > 14 else _AMBER))
        pdf.cell(cols[3][1], 6, str(days), fill=True, align="C")
        pdf.set_text_color(*_DARK)
        pdf.ln()

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)
    pdf.ln(4)


def _governance_metrics(pdf: _BoardReport, data: dict) -> None:
    gov = data.get("governance_metrics", {})
    if not gov:
        return

    pdf.add_page()
    pdf._section("Governance Metrics")

    pdf._stat_block([
        ("Assessments in Review", str(gov.get("assessments_awaiting_review", 0)), _ACCENT),
        ("Approved This Period", str(gov.get("assessments_approved", 0)), _GREEN),
        ("Avg Review Days", f"{gov.get('avg_review_days', 0):.1f}" if gov.get("avg_review_days") else "-", _MID),
        ("Approval Rate", f"{gov.get('approval_rate', 0) * 100:.0f}%" if gov.get("approval_rate") is not None else "-", _GREEN),
    ])

    if gov.get("rejection_rate") is not None:
        pdf._kv("Rejection Rate", f"{gov['rejection_rate'] * 100:.1f}%")
        pdf.ln(1)
    if gov.get("changes_requested_rate") is not None:
        pdf._kv("Changes Requested Rate", f"{gov['changes_requested_rate'] * 100:.1f}%")
        pdf.ln(1)
    pdf.ln(3)


def _action_effectiveness(pdf: _BoardReport, data: dict) -> None:
    eff = data.get("action_effectiveness", {})
    if not eff:
        return

    pdf._section("Action Effectiveness")
    pdf._stat_block([
        ("Opened This Period", str(eff.get("opened_this_period", 0)), _ACCENT),
        ("Closed This Period", str(eff.get("closed_this_period", 0)), _GREEN),
        ("Resolution Rate", f"{eff.get('resolution_rate', 0) * 100:.0f}%" if eff.get("resolution_rate") is not None else "-", _MID),
        ("Avg Resolution Days", f"{eff.get('avg_resolution_days', 0):.1f}" if eff.get("avg_resolution_days") is not None else "-", _MID),
    ])
    pdf.ln(3)


def _kpi_trends(pdf: _BoardReport, data: dict) -> None:
    trends = data.get("kpi_trends", {})
    points = trends.get("data_points", [])
    if not points:
        return

    pdf.add_page()
    pdf._section(f"KPI Trends  ({trends.get('period_days', '-')} days)")

    if trends.get("esg_delta") is not None:
        direction = "+" if trends["esg_delta"] >= 0 else ""
        pdf._kv("ESG Score Change", f"{direction}{trends['esg_delta']:.1f} points")
        pdf.ln(1)
    if trends.get("risk_delta") is not None:
        direction = "+" if trends["risk_delta"] >= 0 else ""
        pdf._kv("Risk Score Change", f"{direction}{trends['risk_delta']:.1f} points")
        pdf.ln(1)
    pdf.ln(4)

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("Month", 25), ("Avg ESG", 25), ("Avg Risk", 25),
        ("Suppliers Scored", 30), ("High+Critical", 30), ("Remaining", usable - 135),
    ]
    pdf._table_header(cols)

    for i, pt in enumerate(points[-12:]):  # show max 12 months
        pdf._row_bg(i)
        dist = pt.get("risk_distribution", {})
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        pdf.cell(cols[0][1], 6, _safe(pt.get("month", ""), 8), fill=True, align="C")
        esg = pt.get("avg_esg_score")
        risk = pt.get("avg_risk_score")
        pdf.cell(cols[1][1], 6, f"{esg:.1f}" if esg is not None else "-", fill=True, align="C")
        pdf.cell(cols[2][1], 6, f"{risk:.1f}" if risk is not None else "-", fill=True, align="C")
        pdf.cell(cols[3][1], 6, str(pt.get("supplier_count", 0)), fill=True, align="C")
        high_crit = pt.get("high_risk_count", 0) + pt.get("critical_risk_count", 0)
        pdf.cell(cols[4][1], 6, str(high_crit), fill=True, align="C")
        low_mod = dist.get("Low", 0) + dist.get("Moderate", 0)
        pdf.cell(cols[5][1], 6, str(low_mod), fill=True, align="C")
        pdf.ln()

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)
    pdf.ln(4)


def _appendix(pdf: _BoardReport, meta: dict, report_id: str) -> None:
    pdf.add_page()
    pdf._section("Appendix — Audit & Provenance")

    pdf.ln(2)
    pdf._subsection("Report Provenance")
    for label, key in [
        ("Report ID", "report_id"),
        ("Report Version", "report_version"),
        ("Generated At", "generated_at"),
        ("Period Start", "period_start"),
        ("Period End", "period_end"),
    ]:
        val = meta.get(key, "-")
        pdf._kv(label, str(val))
        pdf.ln(1)

    pdf.ln(6)
    pdf._subsection("Methodology")
    pdf._body(
        "This report was generated by the EIOS (Enterprise Intelligence Operating System) "
        "platform using deterministic, rule-based calculations.  All ESG and risk scores "
        "are computed from structured assessment data — findings, risks, and open actions — "
        "using the M28 Supplier Intelligence scoring engine (score_version 1.0).  "
        "No machine-learning inference or external model calls are used in metric generation.  "
        "The report_data JSON snapshot stored alongside this PDF contains every raw input "
        "and intermediate value, enabling full reproduction of all figures."
    )
    pdf.ln(6)
    pdf._subsection("Score Methodology Reference")
    pdf._body(
        "ESG Score (0-100, higher = better):  per-pillar deduction model.  "
        "deduction = critical_findings x 12 + high x 6 + medium x 2 + low x 0.5.  "
        "Pillar total = max(0, 100 - deduction).  "
        "ESG Total = (Environmental + Social + Governance) / 3."
    )
    pdf.ln(3)
    pdf._body(
        "Risk Score (0-100, higher = worse):  "
        "raw = critical_findings x 20 + high x 10 + medium x 3 + low x 1 "
        "+ critical_risks x 15 + high_risks x 7 + medium_risks x 2 "
        "+ overdue_actions x 8 + open_actions x 3.  "
        "risk_score = min(100, raw / 5).  "
        "Bands: Low 0-25, Moderate 26-50, High 51-75, Critical 76-100."
    )
    pdf.ln(6)
    pdf._subsection("Immutability Statement")
    pdf._body(
        "Board reports are immutable after generation.  The underlying report_data JSON "
        "snapshot is persisted in the EIOS database and cannot be modified retrospectively.  "
        "This PDF is reproducible from the stored snapshot at any time."
    )

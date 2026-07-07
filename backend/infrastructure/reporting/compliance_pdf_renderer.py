"""M31 Compliance Report PDF Renderer.

Generates compliance gap / readiness reports using fpdf2.
Three report types:
  - CSRD Gap Report
  - ESRS Readiness Report
  - CSDDD Due Diligence Report

Uses the same colour palette and latin-1 safety as the board report renderer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_DARK = (30, 40, 55)
_MID = (80, 95, 110)
_LIGHT = (245, 247, 249)
_ACCENT = (15, 98, 179)
_WHITE = (255, 255, 255)
_GREEN = (40, 130, 60)
_AMBER = (180, 130, 0)
_RED = (180, 30, 30)
_ORANGE = (210, 80, 0)

_STATUS_COLOURS: dict[str, tuple[int, int, int]] = {
    "Compliant": _GREEN,
    "Partially Compliant": _AMBER,
    "Non-Compliant": _RED,
    "Unknown": _MID,
}
_SEVERITY_COLOURS: dict[str, tuple[int, int, int]] = {
    "Critical": _RED,
    "High": _ORANGE,
    "Medium": _AMBER,
    "Low": _GREEN,
}

_UNICODE_MAP = str.maketrans(
    {
        "—": " - ",
        "–": "-",
        "'": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        "•": "*",
        " ": " ",
        "→": "->",
        "≥": ">=",
        "≤": "<=",
    }
)


def _latin1(text: str) -> str:
    return text.translate(_UNICODE_MAP).encode("latin-1", errors="replace").decode("latin-1")


def _safe(val: Any, max_chars: int = 200) -> str:
    s = str(val or "-")
    return _latin1(s[:max_chars] + ("..." if len(s) > max_chars else ""))


class _ComplianceReport(FPDF):
    def __init__(self, report_title: str, org_name: str, generated_at: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._report_title = _latin1(report_title)
        self._org = _latin1(org_name)
        self._generated_at = _latin1(generated_at)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=18, top=15, right=18)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_MID)
        self.cell(0, 6, f"EIOS Compliance Report  |  {self._org}", align="L")
        self.set_x(-80)
        self.cell(0, 6, self._report_title[:55], align="R")
        self.ln(1)
        self.set_draw_color(*_MID)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_MID)
        self.cell(
            0,
            5,
            f"Page {self.page_no()}  |  EIOS Regulatory Intelligence  |  CONFIDENTIAL",
            align="C",
        )

    def cover_page(self, subtitle: str, period: str) -> None:
        self.add_page()
        self.set_fill_color(*_ACCENT)
        self.rect(0, 0, self.w, 60, style="F")
        self.set_y(15)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*_WHITE)
        self.cell(0, 10, self._report_title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 13)
        self.cell(0, 8, _safe(subtitle), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(18)
        self.set_text_color(*_DARK)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 7, _safe(self._org), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_MID)
        if period:
            self.cell(0, 6, _safe(period), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(
            0, 6, f"Generated: {self._generated_at}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )

    def section_heading(self, title: str) -> None:
        self.ln(4)
        self.set_fill_color(*_LIGHT)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*_DARK)
        self.cell(0, 8, _latin1(title), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def kv_row(self, key: str, value: str, *, bold_value: bool = False) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_MID)
        self.cell(55, 6, _latin1(key), new_x=XPos.RIGHT, new_y=YPos.TOP)
        if bold_value:
            self.set_font("Helvetica", "B", 9)
        else:
            self.set_font("Helvetica", "", 9)
        self.set_text_color(*_DARK)
        val_w = max(self.w - self.r_margin - self.x, 1)
        self.multi_cell(val_w, 6, _safe(value, 160), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def status_badge(self, status: str) -> None:
        colour = _STATUS_COLOURS.get(status, _MID)
        self.set_fill_color(*colour)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 7, _latin1(status), fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_DARK)

    def framework_status_table(self, frameworks: list[dict]) -> None:
        self.section_heading("Framework Compliance Status")
        col_widths = [45, 38, 20, 20, 20, 27]
        headers = ["Framework", "Status", "Covered", "Total", "Gaps", "Critical Gaps"]
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        for h, w in zip(headers, col_widths, strict=False):
            self.cell(w, 7, h, fill=True, border=1)
        self.ln()
        self.set_font("Helvetica", "", 8)
        for i, fw in enumerate(frameworks):
            fill = i % 2 == 0
            self.set_fill_color(*(245, 247, 249) if fill else (255, 255, 255))
            self.set_text_color(*_DARK)
            status = fw.get("status", "Unknown")
            colour = _STATUS_COLOURS.get(status, _MID)
            self.cell(
                col_widths[0], 6, _safe(fw.get("regulation_code", ""), 22), fill=fill, border=1
            )
            self.set_text_color(*colour)
            self.cell(col_widths[1], 6, _latin1(status), fill=fill, border=1)
            self.set_text_color(*_DARK)
            self.cell(
                col_widths[2],
                6,
                str(fw.get("covered_requirements", 0)),
                fill=fill,
                border=1,
                align="C",
            )
            self.cell(
                col_widths[3],
                6,
                str(fw.get("total_requirements", 0)),
                fill=fill,
                border=1,
                align="C",
            )
            self.cell(
                col_widths[4], 6, str(fw.get("open_gap_count", 0)), fill=fill, border=1, align="C"
            )
            crit = fw.get("critical_gap_count", 0)
            if crit:
                self.set_text_color(*_RED)
            self.cell(col_widths[5], 6, str(crit), fill=fill, border=1, align="C")
            self.set_text_color(*_DARK)
            self.ln()

    def gap_table(self, gaps: list[dict], title: str = "Compliance Gaps") -> None:
        if not gaps:
            return
        self.section_heading(title)
        col_widths = [55, 50, 20, 40]
        headers = ["Requirement", "Gap Type", "Severity", "Description"]
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        for h, w in zip(headers, col_widths, strict=False):
            self.cell(w, 7, h, fill=True, border=1)
        self.ln()
        self.set_font("Helvetica", "", 7)
        for i, gap in enumerate(gaps[:50]):
            fill = i % 2 == 0
            self.set_fill_color(*(245, 247, 249) if fill else (255, 255, 255))
            self.set_text_color(*_DARK)
            self.cell(
                col_widths[0], 6, _safe(gap.get("requirement_code", ""), 28), fill=fill, border=1
            )
            self.cell(col_widths[1], 6, _safe(gap.get("gap_type", ""), 26), fill=fill, border=1)
            sev = gap.get("severity", "Medium")
            self.set_text_color(*_SEVERITY_COLOURS.get(sev, _DARK))
            self.cell(col_widths[2], 6, _latin1(sev), fill=fill, border=1, align="C")
            self.set_text_color(*_DARK)
            self.cell(col_widths[3], 6, _safe(gap.get("description", ""), 40), fill=fill, border=1)
            self.ln()


def render_csrd_gap_report(
    *,
    org_name: str,
    frameworks: list[dict],
    gaps: list[dict],
    period: str = "",
) -> bytes:
    pdf = _ComplianceReport("CSRD Gap Report", org_name, _now_str())
    pdf.cover_page("Corporate Sustainability Reporting Directive — Gap Analysis", period)
    pdf.add_page()

    pdf.section_heading("Executive Summary")
    total_gaps = len(gaps)
    critical = sum(1 for g in gaps if g.get("severity") == "Critical")
    high = sum(1 for g in gaps if g.get("severity") == "High")
    pdf.kv_row("Organisation", org_name)
    pdf.kv_row("Total Open Gaps", str(total_gaps))
    pdf.kv_row("Critical Gaps", str(critical), bold_value=bool(critical))
    pdf.kv_row("High Priority Gaps", str(high))
    pdf.kv_row("Report Period", period or "All time")

    pdf.framework_status_table(frameworks)

    csrd_gaps = [g for g in gaps if str(g.get("requirement_code", "")).startswith("CSRD")]
    esrs_gaps = [g for g in gaps if str(g.get("requirement_code", "")).startswith("ESRS")]
    pdf.gap_table(csrd_gaps, title="CSRD Directive Gaps")
    pdf.gap_table(esrs_gaps, title="ESRS Reporting Standard Gaps")

    return bytes(pdf.output())


def render_esrs_readiness_report(
    *,
    org_name: str,
    frameworks: list[dict],
    gaps: list[dict],
    period: str = "",
) -> bytes:
    pdf = _ComplianceReport("ESRS Readiness Report", org_name, _now_str())
    pdf.cover_page("European Sustainability Reporting Standards — Readiness Assessment", period)
    pdf.add_page()

    esrs_fw = [f for f in frameworks if f.get("regulation_code") == "ESRS"]
    pdf.section_heading("ESRS Readiness Overview")
    for fw in esrs_fw:
        pdf.kv_row("Status", fw.get("status", "Unknown"), bold_value=True)
        pdf.kv_row(
            "Requirements Covered",
            f"{fw.get('covered_requirements', 0)} / {fw.get('total_requirements', 0)}",
        )
        pdf.kv_row("Coverage Ratio", f"{fw.get('coverage_ratio', 0) * 100:.1f}%")
        pdf.kv_row("Open Gaps", str(fw.get("open_gap_count", 0)))

    esrs_gaps = [g for g in gaps if str(g.get("requirement_code", "")).startswith("ESRS")]
    pdf.framework_status_table(frameworks)
    pdf.gap_table(esrs_gaps, title="ESRS Gaps Requiring Action")

    return bytes(pdf.output())


def render_csddd_due_diligence_report(
    *,
    org_name: str,
    frameworks: list[dict],
    gaps: list[dict],
    period: str = "",
) -> bytes:
    pdf = _ComplianceReport("CSDDD Due Diligence Report", org_name, _now_str())
    pdf.cover_page("Corporate Sustainability Due Diligence — Compliance Status", period)
    pdf.add_page()

    csddd_fw = [f for f in frameworks if f.get("regulation_code") == "CSDDD"]
    pdf.section_heading("Due Diligence Status")
    for fw in csddd_fw:
        pdf.kv_row("Compliance Status", fw.get("status", "Unknown"), bold_value=True)
        pdf.kv_row(
            "Requirements Covered",
            f"{fw.get('covered_requirements', 0)} / {fw.get('total_requirements', 0)}",
        )
        pdf.kv_row("Open Gaps", str(fw.get("open_gap_count", 0)))

    csddd_gaps = [g for g in gaps if str(g.get("requirement_code", "")).startswith("CSDDD")]
    lksg_gaps = [g for g in gaps if str(g.get("requirement_code", "")).startswith("LkSG")]
    pdf.framework_status_table(frameworks)
    pdf.gap_table(csddd_gaps, title="CSDDD Due Diligence Gaps")
    pdf.gap_table(lksg_gaps, title="LkSG Supply Chain Gaps")

    return bytes(pdf.output())


def _now_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

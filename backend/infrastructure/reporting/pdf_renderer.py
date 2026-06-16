"""
EIOS PDF Report Renderer

Produces executive-ready PDF reports from a structured content snapshot.
Layout: Cover -> Executive Summary -> Findings -> Risks -> Recommendations -> Evidence Index -> Audit Trail.

All section data comes from the frozen content_snapshot produced by ReportService,
so the PDF is fully reproducible from the stored JSON alone.

Font note: Uses built-in Helvetica (latin-1 encoding). All text is passed through
_latin1() to replace characters outside that range with safe ASCII equivalents.
"""

from __future__ import annotations

from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos


# ── Colour palette ─────────────────────────────────────────────────────────────
_DARK = (30, 40, 55)
_MID = (80, 95, 110)
_LIGHT = (245, 247, 249)
_ACCENT = (15, 98, 179)
_WHITE = (255, 255, 255)

_LEVEL_COLOURS: dict[str, tuple[int, int, int]] = {
    "Critical": (180, 30, 30),
    "High":     (210, 80,  0),
    "Medium":   (180, 130,  0),
    "Low":      (40, 130, 60),
}

# ── Latin-1 safe text conversion ───────────────────────────────────────────────
_UNICODE_MAP = str.maketrans({
    "—": " - ",   # em dash
    "–": "-",     # en dash
    "‘": "'",     # left single quote
    "’": "'",     # right single quote
    "“": '"',     # left double quote
    "”": '"',     # right double quote
    "…": "...",   # ellipsis
    "•": "*",     # bullet
    " ": " ",     # non-breaking space
    "→": "->",    # arrow
    "°": "deg",   # degree sign
    "®": "(R)",   # registered
    "©": "(C)",   # copyright
    "™": "(TM)",  # trademark
})


def _latin1(text: str) -> str:
    """Replace common Unicode characters with latin-1 safe ASCII equivalents."""
    translated = text.translate(_UNICODE_MAP)
    # Drop any remaining characters not in latin-1 range (replace with ?)
    return translated.encode("latin-1", errors="replace").decode("latin-1")


# ── FPDF subclass ─────────────────────────────────────────────────────────────

class _EIOSReport(FPDF):
    def __init__(self, title: str, generated_by_name: str, generated_at: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._report_title = _latin1(title)
        self._generated_by_name = _latin1(generated_by_name)
        self._generated_at = _latin1(generated_at)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=18, top=15, right=18)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_MID)
        self.cell(0, 6, "EIOS - ESG Due Diligence Report", align="L")
        self.set_x(-60)
        self.cell(0, 6, self._report_title[:50], align="R")
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
        self.cell(0, 5, f"Generated {self._generated_at} by {self._generated_by_name}", align="L")
        self.cell(0, 5, f"Page {self.page_no()}", align="R")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _section_header(self, text: str) -> None:
        self.set_fill_color(*_ACCENT)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, f"  {_latin1(text)}", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.set_text_color(*_DARK)

    def _sub_header(self, text: str) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_MID)
        self.cell(0, 6, _latin1(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_DARK)

    def _body(self, text: str) -> None:
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_DARK)
        self.multi_cell(0, 5, _latin1(text))

    def _kv(self, key: str, value: str) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_MID)
        self.cell(45, 5, _latin1(key) + ":",
                  new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_DARK)
        self.multi_cell(0, 5, _latin1(value))

    def _level_badge(self, level: str, col_w: float) -> None:
        colour = _LEVEL_COLOURS.get(level, _MID)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_WHITE)
        self.set_fill_color(*colour)
        self.cell(col_w, 6, _latin1(level), fill=True, align="C")
        self.set_fill_color(*_WHITE)
        self.set_text_color(*_DARK)

    def _table_header_row(self, cols: list[tuple[str, float]]) -> None:
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 8)
        for label, w in cols:
            self.cell(w, 6, _latin1(label), border=0, fill=True, align="C")
        self.ln()
        self.set_text_color(*_DARK)
        self.set_fill_color(*_LIGHT)

    def _table_row_bg(self, row_idx: int) -> None:
        if row_idx % 2 == 0:
            self.set_fill_color(*_WHITE)
        else:
            self.set_fill_color(*_LIGHT)

    def _safe(self, text: Any, max_chars: int = 300) -> str:
        s = str(text or "-")
        truncated = s[:max_chars] + ("..." if len(s) > max_chars else "")
        return _latin1(truncated)


# ── Public API ─────────────────────────────────────────────────────────────────

def render_report_pdf(snapshot: dict[str, Any]) -> bytes:
    """Render a PDF from the frozen content snapshot and return raw bytes."""
    assessment = snapshot.get("assessment", {})
    findings = snapshot.get("findings", [])
    risks = snapshot.get("risks", [])
    recommendations = snapshot.get("recommendations", [])
    evidence = snapshot.get("evidence", [])
    meta = snapshot.get("meta", {})

    title = assessment.get("title", "ESG Due Diligence Report")
    generated_by_name = meta.get("generated_by_name", "EIOS")
    generated_at = meta.get("generated_at", "")
    report_id = meta.get("report_id", "")

    pdf = _EIOSReport(
        title=title,
        generated_by_name=generated_by_name,
        generated_at=generated_at,
    )

    _cover_page(pdf, assessment, meta)
    _executive_summary(pdf, assessment, findings, risks, recommendations, evidence)
    _findings_section(pdf, findings)
    _risks_section(pdf, risks)
    _recommendations_section(pdf, recommendations)
    _evidence_index(pdf, evidence)
    _audit_trail(pdf, meta, report_id, assessment)

    return bytes(pdf.output())


# ── Sections ──────────────────────────────────────────────────────────────────

def _cover_page(pdf: _EIOSReport, assessment: dict, meta: dict) -> None:
    pdf.add_page()
    pdf.set_fill_color(*_ACCENT)
    pdf.rect(0, 0, 210, 60, "F")

    pdf.set_y(18)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*_WHITE)
    pdf.cell(0, 10, "ESG Due Diligence Report", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Enterprise Intelligence Operating System", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(75)
    pdf.set_text_color(*_DARK)
    pdf.set_font("Helvetica", "B", 16)
    title = _latin1(assessment.get("title", "Untitled Assessment"))
    pdf.multi_cell(0, 10, title, align="C")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_MID)

    rows = [
        ("Assessment Type", assessment.get("assessment_type", "-")),
        ("Scope",           assessment.get("scope", "-")),
        ("Methodology",     assessment.get("methodology") or "-"),
        ("Confidence",      assessment.get("confidence", "-")),
    ]
    for label, value in rows:
        pdf._kv(label, str(value))
        pdf.ln(1)

    pdf.ln(10)
    pdf.set_draw_color(*_ACCENT)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_MID)
    pdf._kv("Generated", meta.get("generated_at", "-"))
    pdf.ln(1)
    pdf._kv("Generated by", meta.get("generated_by_name", "-"))
    pdf.ln(1)
    pdf._kv("Report ID", meta.get("report_id", "-"))
    pdf.ln(12)

    pdf.set_fill_color(255, 243, 205)
    pdf.set_draw_color(200, 160, 0)
    pdf.set_line_width(0.3)
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.w - pdf.l_margin - pdf.r_margin, 14, "FD")
    pdf.set_y(pdf.get_y() + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.cell(0, 4, "CONFIDENTIAL - FOR AUTHORISED RECIPIENTS ONLY", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(
        0, 4,
        "This document contains commercially sensitive information. Do not distribute without authorisation.",
        align="C",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.set_text_color(*_DARK)


def _executive_summary(
    pdf: _EIOSReport,
    assessment: dict,
    findings: list,
    risks: list,
    recommendations: list,
    evidence: list,
) -> None:
    pdf.add_page()
    pdf._section_header("Executive Summary")

    desc = assessment.get("description", "")
    if desc:
        pdf._body(desc)
        pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_MID)
    pdf.cell(0, 6, "Key Figures", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)

    stats = [
        ("Material Findings",   len(findings)),
        ("Identified Risks",    len(risks)),
        ("Recommendations",     len(recommendations)),
        ("Evidence Sources",    len(evidence)),
    ]

    col_w = (pdf.w - pdf.l_margin - pdf.r_margin) / len(stats)
    for label, count in stats:
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*_WHITE)
        pdf.set_fill_color(*_ACCENT)
        pdf.cell(col_w, 14, str(count), fill=True, align="C")
    pdf.ln()
    pdf.set_fill_color(*_DARK)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("Helvetica", "", 8)
    for label, _ in stats:
        pdf.cell(col_w, 6, _latin1(label), fill=True, align="C")
    pdf.ln(6)

    if findings:
        pdf.ln(3)
        pdf._sub_header("Findings by Severity")
        counts: dict[str, int] = {}
        for f in findings:
            lv = f.get("severity", "Medium")
            counts[lv] = counts.get(lv, 0) + 1
        for level in ("Critical", "High", "Medium", "Low"):
            n = counts.get(level, 0)
            if n:
                pdf._level_badge(level, 22)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*_DARK)
                pdf.cell(10, 6, str(n), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    if risks:
        pdf._sub_header("Risks by Level")
        rcounts: dict[str, int] = {}
        for r in risks:
            lv = r.get("risk_level", "Medium")
            rcounts[lv] = rcounts.get(lv, 0) + 1
        for level in ("Critical", "High", "Medium", "Low"):
            n = rcounts.get(level, 0)
            if n:
                pdf._level_badge(level, 22)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*_DARK)
                pdf.cell(10, 6, str(n), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _findings_section(pdf: _EIOSReport, findings: list) -> None:
    if not findings:
        return
    pdf.add_page()
    pdf._section_header(f"Material Findings  ({len(findings)})")

    sorted_findings = sorted(
        findings,
        key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "Medium"), 2),
    )

    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("Sev.", 18),
        ("Title / Description", usable_w - 18 - 28 - 26),
        ("Category", 28),
        ("Confidence", 26),
    ]

    pdf._table_header_row(cols)

    for i, f in enumerate(sorted_findings):
        pdf._table_row_bg(i)
        y_before = pdf.get_y()

        level = f.get("severity", "Medium")
        colour = _LEVEL_COLOURS.get(level, _MID)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*_WHITE)
        pdf.set_fill_color(*colour)
        pdf.cell(cols[0][1], 6, _latin1(level), fill=True, align="C")

        x_after = pdf.get_x()
        pdf.set_font("Helvetica", "B", 8)
        fill_col = _WHITE if i % 2 == 0 else _LIGHT
        pdf.set_fill_color(*fill_col)
        pdf.set_text_color(*_DARK)
        pdf.multi_cell(cols[1][1], 5, pdf._safe(f.get("title", ""), 80), fill=True)
        if f.get("description"):
            pdf.set_x(x_after)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_MID)
            pdf.multi_cell(cols[1][1], 4, pdf._safe(f.get("description", ""), 180), fill=True)
        row_end_y = pdf.get_y()
        row_h = row_end_y - y_before

        pdf.set_xy(x_after + cols[1][1], y_before)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        pdf.set_fill_color(*fill_col)
        pdf.cell(cols[2][1], row_h, pdf._safe(f.get("category", ""), 20), fill=True, align="C")
        pdf.cell(cols[3][1], row_h, _latin1(f.get("confidence", "-")), fill=True, align="C")
        pdf.set_xy(pdf.l_margin, row_end_y)

        if f.get("reasoning"):
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(*_MID)
            pdf.set_x(pdf.l_margin + cols[0][1])
            pdf.multi_cell(
                usable_w - cols[0][1], 4,
                "Reasoning: " + pdf._safe(f["reasoning"], 200),
                fill=False,
            )
        pdf.ln(1)

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)


def _risks_section(pdf: _EIOSReport, risks: list) -> None:
    if not risks:
        return
    pdf.add_page()
    pdf._section_header(f"Risk Assessment  ({len(risks)})")

    sorted_risks = sorted(
        risks,
        key=lambda r: _SEVERITY_ORDER.get(r.get("risk_level", "Medium"), 2),
    )

    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("Level", 18),
        ("Title / Description", usable_w - 18 - 28 - 18 - 18),
        ("Category", 28),
        ("Prob.", 18),
        ("Impact", 18),
    ]

    pdf._table_header_row(cols)

    for i, r in enumerate(sorted_risks):
        pdf._table_row_bg(i)
        y_before = pdf.get_y()

        level = r.get("risk_level", "Medium")
        colour = _LEVEL_COLOURS.get(level, _MID)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*_WHITE)
        pdf.set_fill_color(*colour)
        pdf.cell(cols[0][1], 6, _latin1(level), fill=True, align="C")

        x_after = pdf.get_x()
        fill_col = _WHITE if i % 2 == 0 else _LIGHT
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*fill_col)
        pdf.set_text_color(*_DARK)
        pdf.multi_cell(cols[1][1], 5, pdf._safe(r.get("title", ""), 80), fill=True)
        if r.get("description"):
            pdf.set_x(x_after)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_MID)
            pdf.multi_cell(cols[1][1], 4, pdf._safe(r.get("description", ""), 160), fill=True)
        row_end_y = pdf.get_y()
        row_h = row_end_y - y_before

        pdf.set_xy(x_after + cols[1][1], y_before)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        pdf.set_fill_color(*fill_col)
        pdf.cell(cols[2][1], row_h, pdf._safe(r.get("category", ""), 18), fill=True, align="C")

        prob = r.get("probability")
        imp = r.get("impact")
        pdf.cell(cols[3][1], row_h, f"{prob:.1f}" if prob is not None else "-", fill=True, align="C")
        pdf.cell(cols[4][1], row_h, f"{imp:.1f}" if imp is not None else "-", fill=True, align="C")
        pdf.set_xy(pdf.l_margin, row_end_y)
        pdf.ln(1)

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)


def _recommendations_section(pdf: _EIOSReport, recommendations: list) -> None:
    if not recommendations:
        return
    pdf.add_page()
    pdf._section_header(f"Recommendations  ({len(recommendations)})")

    sorted_recs = sorted(
        recommendations,
        key=lambda r: _SEVERITY_ORDER.get(r.get("priority", "Medium"), 2),
    )

    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("Priority", 20),
        ("Title / Action", usable_w - 20 - 22 - 30),
        ("Required", 22),
        ("Due Date", 30),
    ]

    pdf._table_header_row(cols)

    for i, rec in enumerate(sorted_recs):
        pdf._table_row_bg(i)
        y_before = pdf.get_y()

        priority = rec.get("priority", "Medium")
        colour = _LEVEL_COLOURS.get(priority, _MID)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*_WHITE)
        pdf.set_fill_color(*colour)
        pdf.cell(cols[0][1], 6, _latin1(priority), fill=True, align="C")

        x_after = pdf.get_x()
        fill_col = _WHITE if i % 2 == 0 else _LIGHT
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(*fill_col)
        pdf.set_text_color(*_DARK)
        pdf.multi_cell(cols[1][1], 5, pdf._safe(rec.get("title", ""), 80), fill=True)
        if rec.get("description"):
            pdf.set_x(x_after)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_MID)
            pdf.multi_cell(cols[1][1], 4, pdf._safe(rec.get("description", ""), 160), fill=True)
        row_end_y = pdf.get_y()
        row_h = row_end_y - y_before

        pdf.set_xy(x_after + cols[1][1], y_before)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        pdf.set_fill_color(*fill_col)
        action_required = "Yes" if rec.get("action_required") else "No"
        pdf.cell(cols[2][1], row_h, action_required, fill=True, align="C")
        due_date = rec.get("due_date") or "-"
        if due_date != "-" and "T" in due_date:
            due_date = due_date[:10]
        pdf.cell(cols[3][1], row_h, _latin1(due_date), fill=True, align="C")
        pdf.set_xy(pdf.l_margin, row_end_y)
        pdf.ln(1)

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)


def _evidence_index(pdf: _EIOSReport, evidence: list) -> None:
    if not evidence:
        return
    pdf.add_page()
    pdf._section_header(f"Evidence Index  ({len(evidence)} sources)")

    usable_w = pdf.w - pdf.l_margin - pdf.r_margin
    cols: list[tuple[str, float]] = [
        ("#", 8),
        ("Title", usable_w - 8 - 26 - 22 - 30),
        ("Type", 26),
        ("Confidence", 22),
        ("Source", 30),
    ]

    pdf._table_header_row(cols)

    for i, ev in enumerate(evidence):
        pdf._table_row_bg(i)
        y_before = pdf.get_y()

        fill_col = _WHITE if i % 2 == 0 else _LIGHT
        pdf.set_fill_color(*fill_col)
        pdf.set_text_color(*_DARK)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(cols[0][1], 6, str(i + 1), fill=True, align="C")

        x_after = pdf.get_x()
        pdf.set_font("Helvetica", "B", 8)
        pdf.multi_cell(cols[1][1], 5, pdf._safe(ev.get("title", ""), 70), fill=True)
        if ev.get("description"):
            pdf.set_x(x_after)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_MID)
            pdf.multi_cell(cols[1][1], 4, pdf._safe(ev.get("description", ""), 120), fill=True)
        row_end_y = pdf.get_y()
        row_h = row_end_y - y_before

        pdf.set_xy(x_after + cols[1][1], y_before)
        pdf.set_fill_color(*fill_col)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_DARK)
        pdf.cell(cols[2][1], row_h, pdf._safe(ev.get("evidence_type", ""), 15), fill=True, align="C")
        pdf.cell(cols[3][1], row_h, _latin1(ev.get("confidence", "-")), fill=True, align="C")
        pdf.cell(cols[4][1], row_h, pdf._safe(ev.get("source", ""), 20), fill=True, align="C")
        pdf.set_xy(pdf.l_margin, row_end_y)
        pdf.ln(1)

    pdf.set_text_color(*_DARK)
    pdf.set_fill_color(*_WHITE)


def _audit_trail(pdf: _EIOSReport, meta: dict, report_id: str, assessment: dict) -> None:
    pdf.add_page()
    pdf._section_header("Audit Trail")

    pdf.ln(2)
    pdf._sub_header("Report Provenance")
    pdf._kv("Report ID",     report_id)
    pdf.ln(1)
    pdf._kv("Assessment ID", assessment.get("id", "-"))
    pdf.ln(1)
    pdf._kv("Generated at",  meta.get("generated_at", "-"))
    pdf.ln(1)
    pdf._kv("Generated by",  meta.get("generated_by_name", "-"))
    pdf.ln(1)
    pdf._kv("Generator",     "EIOS Report Service v1 (M18)")
    pdf.ln(6)

    pdf._sub_header("Data Snapshot Integrity")
    pdf._body(
        "This report was produced from a point-in-time snapshot of the EIOS database. "
        "All findings, risks, recommendations, and evidence references were frozen at the "
        "time of generation and stored alongside this PDF. The report can be re-rendered "
        "from the stored snapshot without re-querying the live database, ensuring the "
        "document remains accurate even if underlying records are subsequently updated."
    )
    pdf.ln(6)

    pdf._sub_header("Data Counts at Generation Time")
    counts = meta.get("counts", {})
    for label, key in [
        ("Findings",        "findings"),
        ("Risks",           "risks"),
        ("Recommendations", "recommendations"),
        ("Evidence",        "evidence"),
    ]:
        pdf._kv(label, str(counts.get(key, "-")))
        pdf.ln(1)

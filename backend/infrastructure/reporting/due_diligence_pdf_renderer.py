"""M32.1 Due Diligence Report PDF Renderer.

Generates audit-grade PDF from an immutable snapshot dict.
Always rendered from the stored snapshot — never from live state.
Cursor drift fix applied: set_x(l_margin) + explicit val_w on multi_cell.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

_DARK = (30, 40, 55)
_MID = (80, 95, 110)
_LIGHT = (245, 247, 249)
_ACCENT = (20, 110, 60)  # dark green for due diligence brand
_WHITE = (255, 255, 255)
_GREEN = (40, 130, 60)
_AMBER = (180, 130, 0)
_RED = (180, 30, 30)

_BAND_COLOURS: dict[str, tuple[int, int, int]] = {
    "Critical": _RED,
    "High": _AMBER,
    "Moderate": _AMBER,
    "Low": _GREEN,
}

_UNICODE_MAP = str.maketrans(
    {
        "—": " - ",
        "–": "-",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        "•": "*",
        " ": " ",
        "→": "->",
    }
)


def _latin1(text: str) -> str:
    return text.translate(_UNICODE_MAP).encode("latin-1", errors="replace").decode("latin-1")


def _safe(val: Any, max_chars: int = 200) -> str:
    s = str(val or "-")
    return _latin1(s[:max_chars] + ("..." if len(s) > max_chars else ""))


class _DueDiligencePDF(FPDF):
    def __init__(self, title: str, framework: str, org_name: str, generated_at: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._title = _latin1(title)
        self._framework = _latin1(framework)
        self._org = _latin1(org_name)
        self._generated_at = _latin1(generated_at)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(left=18, top=15, right=18)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_MID)
        self.cell(0, 6, f"EIOS Due Diligence Report  |  {self._org}", align="L")
        self.set_x(-80)
        self.cell(0, 6, self._framework[:40], align="R")
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
            f"Page {self.page_no()}  |  EIOS Due Diligence Report  |  CONFIDENTIAL",
            align="C",
        )

    def cover_page(self, report_type: str, generated_at: str) -> None:
        self.add_page()
        self.set_fill_color(*_ACCENT)
        self.rect(0, 0, self.w, 60, style="F")
        self.set_y(15)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*_WHITE)
        self.cell(0, 10, self._title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 12)
        self.cell(0, 8, _safe(report_type), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(16)
        self.set_text_color(*_DARK)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 7, _safe(self._org), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_MID)
        self.cell(
            0, 6, f"Generated: {generated_at}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
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

    def metric_row(self, label: str, value: str, band: str | None = None) -> None:
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_MID)
        self.cell(100, 6, _latin1(label), new_x=XPos.RIGHT, new_y=YPos.TOP)
        colour = _BAND_COLOURS.get(band or "", _DARK) if band else _DARK
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*colour)
        val_w = max(self.w - self.r_margin - self.x, 1)
        self.multi_cell(val_w, 6, _safe(value, 80), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_DARK)

    def explainability_section(self, items: list[dict]) -> None:
        self.section_heading("Explainability & Audit Trail")
        for item in items:
            self.set_x(self.l_margin)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*_DARK)
            factor = _safe(str(item.get("factor") or item.get("conclusion") or ""), 60)
            self.cell(60, 5, factor)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*_MID)
            val_w = max(self.w - self.r_margin - self.x, 1)
            desc = _safe(str(item.get("description") or item.get("detail") or ""), 200)
            self.multi_cell(val_w, 5, desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_DARK)


def _report_type_title(report_type: str, framework: str) -> str:
    titles = {
        "lksgg_annual": "LkSG Annual Due Diligence Report",
        "csddd": "CSDDD Due Diligence Report",
        "human_rights": "Human Rights Risk Report",
        "environmental": "Environmental Risk Report",
        "preventive_measures": "Preventive Measures Register",
        "remediation": "Remediation Progress Report",
    }
    return titles.get(report_type, f"{framework} Due Diligence Report")


def render_due_diligence_report(
    *,
    org_name: str,
    report: dict,
) -> bytes:
    """Render a due diligence report snapshot to PDF bytes.

    Always rendered from the immutable snapshot stored at generation time.
    """
    meta = report.get("meta", {})
    framework = meta.get("framework", "")
    framework_version = meta.get("framework_version", "")
    report_type = meta.get("report_type", "")
    meta.get("organization_id", "")
    generated_at = meta.get("generated_at", _now_str())
    reporting_year = meta.get("reporting_year", "")

    title = _report_type_title(report_type, framework)
    subtitle = f"{framework} {framework_version}".strip() if framework_version else framework

    pdf = _DueDiligencePDF(title, subtitle or title, org_name, generated_at)
    pdf.cover_page(subtitle or title, generated_at)
    pdf.add_page()

    # ── Report Overview ────────────────────────────────────────────────────
    pdf.section_heading("Report Overview")
    pdf.kv_row("Organisation", org_name)
    pdf.kv_row("Framework", framework)
    if framework_version:
        pdf.kv_row("Framework Version", framework_version)
    if reporting_year:
        pdf.kv_row("Reporting Year", str(reporting_year))
    pdf.kv_row("Generated", generated_at)

    # ── Summary section ────────────────────────────────────────────────────
    summary = report.get("summary", {})
    if summary:
        pdf.section_heading("Executive Summary")
        for key, val in summary.items():
            if val is not None:
                label = key.replace("_", " ").title()
                pdf.metric_row(label, str(val))

    # ── Supplier inventory / supply chain ──────────────────────────────────
    supplier_section = report.get("supplier_inventory") or report.get("supply_chain")
    if supplier_section:
        pdf.section_heading("Supply Chain Overview")
        pdf.metric_row(
            "Total Suppliers",
            str(supplier_section.get("total", supplier_section.get("total_suppliers", 0))),
        )
        for tier, count in (supplier_section.get("by_tier") or {}).items():
            pdf.metric_row(f"  {tier}", str(count))

    # ── Risk classification ────────────────────────────────────────────────
    risk_class = report.get("risk_classification") or report.get("risk_assessment")
    if risk_class:
        pdf.section_heading("Risk Classification")
        for band, val in risk_class.items():
            label = band.replace("_", " ").title()
            colour = (
                "Critical"
                if "critical" in band.lower()
                else ("High" if "high" in band.lower() else None)
            )
            pdf.metric_row(label, str(val), band=colour)

    # ── Human rights ──────────────────────────────────────────────────────
    hr = report.get("human_rights")
    if hr:
        pdf.section_heading("Human Rights Findings")
        pdf.metric_row(
            "Total HR Findings",
            str(hr.get("total_findings", 0)),
            band="Critical" if hr.get("critical_findings", 0) > 0 else None,
        )
        pdf.metric_row("Critical HR Findings", str(hr.get("critical_findings", 0)))
        pdf.metric_row("Suppliers Impacted", str(hr.get("suppliers_impacted", 0)))

    # ── By topic (HR or Env) ──────────────────────────────────────────────
    by_topic = report.get("by_topic", [])
    if by_topic:
        pdf.section_heading("Findings by Topic")
        for topic_row in by_topic[:10]:
            label = topic_row.get("display_name") or topic_row.get("topic", "")
            count = topic_row.get("finding_count", 0)
            critical = topic_row.get("critical_findings", 0)
            pdf.metric_row(
                _safe(label, 40),
                f"{count} findings ({critical} critical)",
                band="Critical" if critical > 0 else None,
            )

    # ── Environmental ─────────────────────────────────────────────────────
    env = report.get("environmental")
    if env:
        pdf.section_heading("Environmental Findings")
        pdf.metric_row("Total Env Findings", str(env.get("total_findings", 0)))
        pdf.metric_row("Critical Env Findings", str(env.get("critical_findings", 0)))
        pdf.metric_row("Suppliers Impacted", str(env.get("suppliers_impacted", 0)))

    # ── Severe impacts (CSDDD) ────────────────────────────────────────────
    severe = report.get("severe_impacts")
    if severe:
        pdf.section_heading("Severe Adverse Impacts")
        pdf.metric_row(
            "Total Severe Impacts",
            str(severe.get("total", 0)),
            band="Critical" if severe.get("critical", 0) > 0 else None,
        )
        pdf.metric_row("  Human Rights", str(severe.get("human_rights", 0)))
        pdf.metric_row("  Environmental", str(severe.get("environmental", 0)))

    # ── Remediation ───────────────────────────────────────────────────────
    rem = report.get("remediation") or report.get("remediation_progress")
    if rem:
        pdf.section_heading("Remediation Progress")
        total = rem.get("total", 0)
        completed = rem.get("completed", rem.get("resolved", 0))
        open_r = rem.get("open", 0)
        overdue = rem.get("overdue", 0)
        closure = rem.get("closure_rate", 0)
        pdf.metric_row("Total Actions", str(total))
        pdf.metric_row("Completed", str(completed))
        pdf.metric_row("Open", str(open_r))
        pdf.metric_row("Overdue", str(overdue), band="Critical" if overdue > 0 else None)
        pdf.metric_row("Closure Rate", f"{closure:.1%}")

    # ── Critical suppliers ────────────────────────────────────────────────
    critical_suppliers = report.get("critical_suppliers", [])
    if critical_suppliers:
        pdf.add_page()
        pdf.section_heading("Critical & High-Risk Suppliers")
        for s in critical_suppliers[:15]:
            band = s.get("risk_band", "")
            colour = _BAND_COLOURS.get(band, _MID)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*colour)
            pdf.cell(35, 5, _safe(band, 12))
            pdf.set_text_color(*_DARK)
            pdf.cell(90, 5, _safe(s.get("supplier_name", ""), 50))
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*_MID)
            pdf.cell(
                0,
                5,
                f"Risk: {s.get('risk_score', 0):.1f}  ESG: {s.get('esg_score', 100):.1f}",
                align="R",
            )
            pdf.ln()

    # ── Explainability ────────────────────────────────────────────────────
    explainability = report.get("explainability", [])
    if explainability:
        pdf.add_page()
        pdf.explainability_section(explainability)

    return bytes(pdf.output())


def _now_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

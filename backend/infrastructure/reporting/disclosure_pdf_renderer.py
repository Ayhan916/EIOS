"""M32 Reporting Package PDF Renderer.

Generates a disclosure-ready reporting package PDF from a stored snapshot dict.
Always rendered from the immutable snapshot stored at publication time —
never from live database state, ensuring reproducibility.
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

_STATUS_COLOURS: dict[str, tuple[int, int, int]] = {
    "Published": _GREEN,
    "Approved": _GREEN,
    "In Review": _AMBER,
    "Draft": _AMBER,
    "Not Started": _MID,
    "Blocked": _RED,
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
        " ": " ",
        "→": "->",
    }
)


def _latin1(text: str) -> str:
    return text.translate(_UNICODE_MAP).encode("latin-1", errors="replace").decode("latin-1")


def _safe(val: Any, max_chars: int = 200) -> str:
    s = str(val or "-")
    return _latin1(s[:max_chars] + ("..." if len(s) > max_chars else ""))


class _PackagePDF(FPDF):
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
        self.cell(0, 6, f"EIOS Sustainability Report  |  {self._org}", align="L")
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
            f"Page {self.page_no()}  |  EIOS Reporting Package  |  CONFIDENTIAL",
            align="C",
        )

    def cover_page(self, subtitle: str, generated_at: str) -> None:
        self.add_page()
        self.set_fill_color(*_ACCENT)
        self.rect(0, 0, self.w, 60, style="F")
        self.set_y(15)
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*_WHITE)
        self.cell(0, 10, self._title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 12)
        self.cell(0, 8, _safe(subtitle), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
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

    def disclosure_item(
        self, ref: str, title: str, status: str, narrative: str, coverage: float
    ) -> None:
        self.ln(2)
        colour = _STATUS_COLOURS.get(status, _MID)
        # Reference + status badge
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_DARK)
        self.cell(80, 6, _safe(ref, 30))
        self.set_fill_color(*colour)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 7)
        self.cell(30, 6, _latin1(status), fill=True, align="C")
        cov_pct = f"{coverage:.0%}"
        self.set_fill_color(*_LIGHT)
        self.set_text_color(*_DARK)
        self.cell(25, 6, f"Coverage: {cov_pct}", fill=True, align="C")
        self.ln()
        # Title
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_DARK)
        w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 5, _safe(title, 80), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Narrative
        if narrative and narrative.strip():
            self.set_x(self.l_margin + 4)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*_MID)
            avail = w - 4
            self.multi_cell(avail, 5, _safe(narrative, 300), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_DARK)

    def summary_table(self, by_status: dict[str, int], total: int) -> None:
        self.section_heading("Disclosure Summary")
        col_widths = [60, 30, 30, 30, 30]
        headers = ["Status", "Count", "% of Total"]
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        for h, w in zip(headers, col_widths[:3], strict=False):
            self.cell(w, 7, h, fill=True, border=1)
        self.ln()
        self.set_font("Helvetica", "", 8)
        for st in ["Published", "Approved", "In Review", "Draft", "Not Started"]:
            cnt = by_status.get(st, 0)
            pct = f"{cnt / total * 100:.1f}%" if total else "0%"
            colour = _STATUS_COLOURS.get(st, _MID)
            self.set_text_color(*colour)
            self.cell(col_widths[0], 6, _latin1(st), border=1)
            self.set_text_color(*_DARK)
            self.cell(col_widths[1], 6, str(cnt), border=1, align="C")
            self.cell(col_widths[2], 6, pct, border=1, align="C")
            self.ln()
        self.set_text_color(*_DARK)


def render_reporting_package(
    *,
    org_name: str,
    package: dict,
) -> bytes:
    meta = package.get("meta", {})
    framework_code = meta.get("framework_code", "")
    framework_name = f"{framework_code} Sustainability Reporting Package"
    generated_at = meta.get("generated_at", _now_str())
    fw_version = meta.get("fw_version", "1.0")
    package_type = meta.get("package_type", "")
    total_reqs = meta.get("total_requirements", 0)
    published_count = meta.get("published_count", 0)
    approved_count = meta.get("approved_count", 0)

    requirements: list[dict] = package.get("requirements", [])

    pdf = _PackagePDF(framework_name, framework_code, org_name, generated_at)
    pdf.cover_page(f"{framework_code} — Version {fw_version}", generated_at)
    pdf.add_page()

    pdf.section_heading("Package Overview")
    pdf.kv_row("Organisation", org_name)
    pdf.kv_row("Framework", framework_code)
    pdf.kv_row("Framework Version", fw_version)
    pdf.kv_row("Package Type", package_type)
    pdf.kv_row("Generated", generated_at)
    pdf.kv_row("Total Requirements", str(total_reqs))
    pdf.kv_row("Published", str(published_count), bold_value=True)
    pdf.kv_row("Approved", str(approved_count))
    completion_pct = f"{published_count / total_reqs * 100:.1f}%" if total_reqs else "0%"
    pdf.kv_row("Completion", completion_pct, bold_value=True)

    # Summary table
    by_status: dict[str, int] = {}
    for r in requirements:
        st = r.get("disclosure_status", "Not Started")
        by_status[st] = by_status.get(st, 0) + 1
    if requirements:
        pdf.summary_table(by_status, len(requirements))

    # Category sections
    categories = {}
    for req in requirements:
        cat = req.get("category", "General")
        categories.setdefault(cat, []).append(req)

    for cat, reqs in sorted(categories.items()):
        pdf.add_page()
        pdf.section_heading(f"{cat} Disclosures")
        for req in reqs:
            pdf.disclosure_item(
                ref=req.get("reference", ""),
                title=req.get("title", ""),
                status=req.get("disclosure_status", "Not Started"),
                narrative=req.get("narrative_text", ""),
                coverage=req.get("evidence_coverage", 0.0),
            )

    return bytes(pdf.output())


def _now_str() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

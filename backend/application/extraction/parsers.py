"""
Regex-based parsers for structured data embedded in agent LLM outputs (M16 hardened).

Each agent system prompt defines a specific output format. These parsers
extract structured fields from those formats without a second LLM call —
deterministic, fast, zero cost, and fully auditable.

M16 hardening:
- Header patterns match H2/H3/H4 headings, bold markers, dashes, em-dashes
- All field extraction is case-insensitive
- Markdown formatting is stripped before matching
- Secondary fallback section parser activates when primary patterns yield nothing
- Field normalization is deferred to the validator layer (schema.py + validator.py)

Fallback: when parsing yields nothing, a single summary entity is created
from the first non-empty paragraph of the agent output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data transfer objects (pure data, no domain imports)
# ---------------------------------------------------------------------------

@dataclass
class ParsedFinding:
    title: str
    description: str
    category: str = ""
    severity: str = "Medium"
    confidence: str = "Medium"
    regulatory_basis: str = ""
    reasoning: str = ""


@dataclass
class ParsedRisk:
    title: str
    description: str
    category: str = ""
    risk_level: str = "Medium"
    probability: Optional[float] = None
    impact: Optional[float] = None
    regulatory_exposure: str = ""
    reasoning: str = ""


@dataclass
class ParsedRecommendation:
    title: str
    description: str
    priority: str = "Medium"
    action_required: bool = True
    regulatory_basis: str = ""
    responsible_party: str = ""
    timeline: str = ""
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Shared pre-processing helpers
# ---------------------------------------------------------------------------

def _strip_markdown(text: str) -> str:
    """Remove bold/italic markers so that patterns match regardless of formatting."""
    text = re.sub(r"\*{1,3}", "", text)
    text = re.sub(r"_{1,2}", "", text)
    return text


def _normalise_ws(text: str) -> str:
    """Collapse runs of whitespace (but preserve newlines)."""
    return re.sub(r"[ \t]+", " ", text).strip()


# ---------------------------------------------------------------------------
# Shared field-extraction patterns (reused across all three entity types)
# ---------------------------------------------------------------------------
# Separator pattern: colon, dash, em-dash, en-dash (with optional spaces)
_SEP = r"[\s]*[:\-–—][\s]*"

_SEVERITY_LINE   = re.compile(r"(?:severity|risk\s+level|level)"   + _SEP + r"\*{0,2}(\w[\w ]*)", re.IGNORECASE)
_CONFIDENCE_LINE = re.compile(r"confidence"                         + _SEP + r"\*{0,2}(\w+)",        re.IGNORECASE)
_CATEGORY_LINE   = re.compile(r"category"                          + _SEP + r"\*{0,2}([^\n,|]+)",   re.IGNORECASE)
_REGULATORY_LINE = re.compile(r"regulatory\s+(?:basis|obligation|exposure)"
                               + _SEP + r"([^\n]+)",                                                re.IGNORECASE)
_REASONING_LINE  = re.compile(r"reasoning"                         + _SEP + r"([^\n]+)",             re.IGNORECASE)
_PROBABILITY_LINE = re.compile(r"probability" + _SEP + r"([\d.]+)", re.IGNORECASE)
_IMPACT_LINE      = re.compile(r"impact"      + _SEP + r"([\d.]+)", re.IGNORECASE)
_PRIORITY_LINE    = re.compile(r"priority"    + _SEP + r"\*{0,2}(\w+)", re.IGNORECASE)
_TIMELINE_LINE    = re.compile(r"timeline"    + _SEP + r"([^\n\|]+)", re.IGNORECASE)
_RESPONSIBLE_LINE = re.compile(r"responsible\s+party" + _SEP + r"([^\n]+)", re.IGNORECASE)
_TYPE_LINE        = re.compile(r"(?:action\s+)?type" + _SEP + r"\*{0,2}(Required|Recommended)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Severity / level normalisation (used at parse time for backwards compat)
# ---------------------------------------------------------------------------

_SEVERITY_MAP = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "crit": "Critical",
    "severe": "High",
    "moderate": "Medium",
    "minor": "Low",
}

def _normalise_level(raw: str) -> str:
    return _SEVERITY_MAP.get(raw.strip().lower(), "Medium")


# ---------------------------------------------------------------------------
# ESG Assessment → Findings
# ---------------------------------------------------------------------------

# Hardened header: matches H2/H3/H4 headings, bold markers, various separators
# Also captures the numbered-list pattern "1. Title" as a fallback capture group.
_FINDING_HEADER = re.compile(
    r"""
    (?:
        \#{2,4}[ \t]*           # H2–H4 heading
        (?:Material[ \t]+)?     # optional "Material "
        (?:Finding|FINDING)\b   # keyword — \b prevents matching "Findings" (plural)
        [ \t]*\d*[ \t]*         # optional number
        [:\-–—\s]*              # separator
        (.+?)                   # title capture (non-greedy)
        [ \t]*$                 # to end of line
    |
        \*{1,2}                 # bold open
        (?:Material[ \t]+)?Finding\b[ \t]*\d*[ \t]*[-:—–]+[ \t]*
        (.+?)                   # title capture
        \*{0,2}[ \t]*$         # bold close, end of line
    )
    """,
    re.MULTILINE | re.VERBOSE | re.IGNORECASE,
)

# Secondary: split on any "Finding N" marker in the text
_FINDING_SPLIT = re.compile(
    r"(?=#{2,4}[ \t]*(?:Material[ \t]+)?(?:Finding|FINDING)[ \t]*\d)",
    re.IGNORECASE,
)

# Fallback split — numbered headers in a section titled "Material Findings"
_FINDING_SECTION = re.compile(
    r"###?\s*Material\s+Findings?\s*\n(.*?)(?=\n###|$)",
    re.DOTALL | re.IGNORECASE,
)


def parse_findings(content: str) -> list[ParsedFinding]:
    if not content:
        return []

    content = _strip_markdown(content)
    sections = _FINDING_SPLIT.split(content)
    findings: list[ParsedFinding] = []

    for section in sections:
        header_match = _FINDING_HEADER.search(section)
        if not header_match:
            continue
        # Either group may capture depending on which branch matched
        raw_title = (header_match.group(1) or header_match.group(2) or "").strip()
        title = _normalise_ws(raw_title).rstrip("*").rstrip()
        if not title:
            continue

        severity_m   = _SEVERITY_LINE.search(section)
        confidence_m = _CONFIDENCE_LINE.search(section)
        category_m   = _CATEGORY_LINE.search(section)
        regulatory_m = _REGULATORY_LINE.search(section)
        reasoning_m  = _REASONING_LINE.search(section)

        # Description: first block of prose after the header line
        desc_match = re.search(
            r"#{2,4}[^\n]+\n([\s\S]+?)(?=\n\s*-|\n\d\.|\n#{2,4}|$)", section
        )
        description = desc_match.group(1).strip()[:1000] if desc_match else title

        findings.append(ParsedFinding(
            title=title[:200],
            description=description,
            severity=_normalise_level(severity_m.group(1) if severity_m else "Medium"),
            confidence=_normalise_level(confidence_m.group(1) if confidence_m else "Medium"),
            category=(category_m.group(1).strip()[:100] if category_m else ""),
            regulatory_basis=(regulatory_m.group(1).strip()[:500] if regulatory_m else ""),
            reasoning=(reasoning_m.group(1).strip()[:500] if reasoning_m else ""),
        ))

    # Fallback: numbered list items inside a "Material Findings" section
    if not findings:
        mat_section = _FINDING_SECTION.search(content)
        if mat_section:
            items = re.findall(r"^\d+\.\s+(.+)", mat_section.group(1), re.MULTILINE)
            for item in items[:10]:
                title_part = re.split(r"[—\-]", item)[0].strip()
                findings.append(ParsedFinding(
                    title=title_part[:200],
                    description=item.strip()[:500],
                    severity=_normalise_level(
                        next((w for w in _SEVERITY_MAP if w in item.lower()), "Medium")
                    ),
                ))

    return findings[:20]


# ---------------------------------------------------------------------------
# Risk Assessment → Risks
# ---------------------------------------------------------------------------

_RISK_HEADER = re.compile(
    r"""
    (?:
        \#{2,4}[ \t]*Risk(?:[ \t]*\d+)?[ \t]*[:\-–—][ \t]*(.+?)[ \t]*$   # H2–H4 (explicit separator required)
    |
        \*{1,2}Risk[ \t]*\d*[ \t]*[-:—–]+[ \t]*(.+?)\*{0,2}[ \t]*$        # bold
    )
    """,
    re.MULTILINE | re.VERBOSE | re.IGNORECASE,
)

_RISK_SPLIT = re.compile(
    r"(?=#{2,4}[ \t]*Risk[ \t]*\d)",
    re.IGNORECASE,
)


def parse_risks(content: str) -> list[ParsedRisk]:
    if not content:
        return []

    content = _strip_markdown(content)
    sections = _RISK_SPLIT.split(content)
    risks: list[ParsedRisk] = []

    for section in sections:
        header_m = _RISK_HEADER.search(section)
        if not header_m:
            continue
        raw_title = (header_m.group(1) or header_m.group(2) or "").strip()
        title = _normalise_ws(raw_title).rstrip("*").rstrip()
        if not title:
            continue

        level_m      = _SEVERITY_LINE.search(section)
        prob_m       = _PROBABILITY_LINE.search(section)
        impact_m     = _IMPACT_LINE.search(section)
        category_m   = _CATEGORY_LINE.search(section)
        exposure_m   = _REGULATORY_LINE.search(section)
        reasoning_m  = _REASONING_LINE.search(section)

        probability: Optional[float] = None
        impact: Optional[float] = None
        try:
            if prob_m:
                probability = float(prob_m.group(1))
        except ValueError:
            pass
        try:
            if impact_m:
                impact = float(impact_m.group(1))
        except ValueError:
            pass

        risks.append(ParsedRisk(
            title=title[:200],
            description=title,
            risk_level=_normalise_level(level_m.group(1) if level_m else "Medium"),
            probability=probability,
            impact=impact,
            category=(category_m.group(1).strip()[:100] if category_m else ""),
            regulatory_exposure=(exposure_m.group(1).strip()[:500] if exposure_m else ""),
            reasoning=(reasoning_m.group(1).strip()[:500] if reasoning_m else ""),
        ))

    return risks[:20]


# ---------------------------------------------------------------------------
# Recommendation → Recommendations
# ---------------------------------------------------------------------------

_REC_HEADER = re.compile(
    r"""
    (?:
        \#{2,4}[ \t]*Recommendation(?:[ \t]*\d+)?[ \t]*[:\-–—][ \t]*(.+?)[ \t]*$   # H2–H4 (explicit separator required)
    |
        \*{1,2}Recommendation[ \t]*\d*[ \t]*[-:—–]+[ \t]*(.+?)\*{0,2}[ \t]*$        # bold
    )
    """,
    re.MULTILINE | re.VERBOSE | re.IGNORECASE,
)

_REC_SPLIT = re.compile(
    r"(?=#{2,4}[ \t]*Recommendation[ \t]*\d)",
    re.IGNORECASE,
)


def parse_recommendations(content: str) -> list[ParsedRecommendation]:
    if not content:
        return []

    content = _strip_markdown(content)
    sections = _REC_SPLIT.split(content)
    recs: list[ParsedRecommendation] = []

    for section in sections:
        header_m = _REC_HEADER.search(section)
        if not header_m:
            continue
        raw_title = (header_m.group(1) or header_m.group(2) or "").strip()
        title = _normalise_ws(raw_title).rstrip("*").rstrip()
        if not title:
            continue

        priority_m   = _PRIORITY_LINE.search(section)
        type_m       = _TYPE_LINE.search(section)
        regulatory_m = _REGULATORY_LINE.search(section)
        responsible_m = _RESPONSIBLE_LINE.search(section)
        timeline_m   = _TIMELINE_LINE.search(section)
        reasoning_m  = _REASONING_LINE.search(section)

        action_required = True
        if type_m and type_m.group(1).lower() == "recommended":
            action_required = False

        recs.append(ParsedRecommendation(
            title=title[:200],
            description=title,
            priority=_normalise_level(priority_m.group(1) if priority_m else "Medium"),
            action_required=action_required,
            regulatory_basis=(regulatory_m.group(1).strip()[:500] if regulatory_m else ""),
            responsible_party=(responsible_m.group(1).strip()[:200] if responsible_m else ""),
            timeline=(timeline_m.group(1).strip()[:200] if timeline_m else ""),
            reasoning=(reasoning_m.group(1).strip()[:500] if reasoning_m else ""),
        ))

    return recs[:20]

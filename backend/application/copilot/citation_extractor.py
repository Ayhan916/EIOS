"""Citation extractor — parses structured citations from LLM responses.

Pure function, no I/O. Citations are embedded in the answer as [Type:id] tags.
"""

from __future__ import annotations

import re

from domain.enums import CitationType

_CITATION_PATTERN = re.compile(
    r"\[(" + "|".join(re.escape(t.value) for t in CitationType) + r"):([a-zA-Z0-9_-]+)\]"
)

_VALID_TYPES = frozenset(t.value for t in CitationType)


def extract_citations(
    content: str,
    citation_map: dict[str, str],
) -> list[dict]:
    """Extract [Type:id] citation tags from LLM answer text.

    Also includes any source IDs from retrieval that appear in the content
    (fuzzy matching for IDs mentioned without brackets).

    Returns list of dicts: {citation_type, object_id, relevance}
    """
    found: dict[str, dict] = {}

    # Explicit [Type:id] citations from LLM output — only accepted if the ID
    # appears in citation_map (prevents the LLM from hallucinating source IDs)
    for match in _CITATION_PATTERN.finditer(content):
        citation_type, obj_id = match.group(1), match.group(2)
        if citation_type in _VALID_TYPES and obj_id in citation_map:
            found[obj_id] = {
                "citation_type": citation_type,
                "object_id": obj_id,
                "relevance": "explicit",
            }

    # Source IDs from retrieval that appear in the content
    for source_id, ctype in citation_map.items():
        if source_id and source_id in content and source_id not in found:
            found[source_id] = {
                "citation_type": ctype,
                "object_id": source_id,
                "relevance": "retrieved",
            }

    return list(found.values())


def format_citations_for_prompt(citation_map: dict[str, str]) -> str:
    """Format available citations for inclusion in the system prompt."""
    if not citation_map:
        return ""
    lines = ["Available source objects you may cite as [Type:id]:"]
    for obj_id, ctype in list(citation_map.items())[:50]:  # cap at 50
        lines.append(f"  [{ctype}:{obj_id}]")
    return "\n".join(lines)

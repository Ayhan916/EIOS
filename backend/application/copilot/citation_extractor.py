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

    # All retrieved source IDs are implicitly cited — the LLM no longer writes
    # inline [Type:id] tags, so we register every retrieved object as a source.
    for source_id, ctype in citation_map.items():
        if source_id and source_id not in found:
            found[source_id] = {
                "citation_type": ctype,
                "object_id": source_id,
                "relevance": "retrieved",
            }

    return list(found.values())


def format_citations_for_prompt(citation_map: dict[str, str]) -> str:
    """Format available citations for inclusion in the system prompt.

    We no longer ask the LLM to write [Type:id] tags inline — citations are
    extracted implicitly from source IDs that appear in the assembled context.
    This function now returns an empty string so no citation instruction is
    injected into the prompt, keeping the answer text clean.
    """
    return ""

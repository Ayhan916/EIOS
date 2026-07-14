"""PromptVersion domain value object (ADR-011).

Immutable representation of one versioned prompt template.
Rendering happens via `str.format_map()` — no templating library required.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PromptVersion:
    """One immutable version of a named prompt template.

    Attributes:
        prompt_name: Stable logical name (e.g. "financial_extraction_system").
        version:     Monotonically increasing integer. Higher = newer.
        template:    Prompt text with optional `{variable}` placeholders.
        variables:   Declared placeholders — validated before rendering.
        active:      Only one version per prompt_name is active at a time.
        created_at:  When this version was created (for audit trail).
    """

    prompt_name: str
    version: int
    template: str
    variables: tuple[str, ...]
    active: bool
    created_at: datetime

"""M47 G-013 — Audit Trail CSV/Excel Export.

StreamingResponse for small/medium exports (<10k rows).
For large exports, a Celery background task is preferred.

CSV columns:
  timestamp, action, actor_email, actor_id, entity_type, entity_id,
  outcome, detail, organization_id

The export is scoped to the authenticated org and requires Admin role.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

_CSV_COLUMNS = [
    "timestamp",
    "action",
    "actor_email",
    "actor_id",
    "entity_type",
    "entity_id",
    "outcome",
    "detail",
]

_MAX_DETAIL_CHARS = 1000


def stream_audit_csv(events: list[dict[str, Any]]) -> str:
    """Convert a list of audit event dicts to CSV string.

    Args:
        events: list of dicts with keys matching AuditEventModel columns
                (created_at, action, actor_email, actor_id, entity_type,
                entity_id, outcome, detail).

    Returns:
        UTF-8 CSV string (header + rows).
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()

    for event in events:
        ts = event.get("created_at")
        if isinstance(ts, datetime):
            ts = ts.isoformat()

        detail = event.get("detail") or ""
        if len(detail) > _MAX_DETAIL_CHARS:
            detail = detail[:_MAX_DETAIL_CHARS] + "…"

        writer.writerow(
            {
                "timestamp": ts or "",
                "action": event.get("action", ""),
                "actor_email": event.get("actor_email", ""),
                "actor_id": event.get("actor_id", ""),
                "entity_type": event.get("entity_type", ""),
                "entity_id": event.get("entity_id", ""),
                "outcome": event.get("outcome", ""),
                "detail": detail,
            }
        )

    return output.getvalue()


def make_csv_filename(
    start: str | None,
    end: str | None,
    entity_type: str | None,
) -> str:
    """Generate a descriptive filename for the audit export."""
    parts = ["eios_audit_trail"]
    if entity_type:
        parts.append(entity_type.lower())
    if start:
        parts.append(start[:10])
    if end:
        parts.append(end[:10])
    return "_".join(parts) + ".csv"

"""Remediation Tracking Engine — M32.1.

Aggregates open, completed, and overdue remediation actions.
All functions are pure: no I/O, no side effects.
"""

from __future__ import annotations

_OPEN_STATUSES = frozenset({"open"})
_IN_PROGRESS_STATUSES = frozenset({"in_progress"})
_RESOLVED_STATUSES = frozenset({"resolved", "verified"})


def _priority_order(priority: str) -> int:
    return {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(priority, 0)


def build_remediation_report(
    *,
    organization_id: str,
    recommendations: list[dict],
) -> dict:
    """Aggregate remediation tracking from recommendations.

    Args:
        recommendations: list of {id, title, action_status, due_date, priority,
                                   supplier_id, overdue, resolution_days}
            - action_status: "open" | "in_progress" | "resolved" | "verified"
            - overdue: bool — whether the action is past due_date and not resolved
            - resolution_days: int | None — days from creation to resolution (for resolved items)

    Returns:
        Serialisable snapshot dict.
    """
    open_items = [r for r in recommendations if r.get("action_status") in _OPEN_STATUSES]
    in_progress_items = [r for r in recommendations if r.get("action_status") in _IN_PROGRESS_STATUSES]
    completed_items = [r for r in recommendations if r.get("action_status") in _RESOLVED_STATUSES]
    overdue_items = [
        r for r in recommendations
        if r.get("action_status") in (_OPEN_STATUSES | _IN_PROGRESS_STATUSES) and r.get("overdue", False)
    ]

    total = len(recommendations)
    total_active = len(open_items) + len(in_progress_items)
    closure_rate = round(len(completed_items) / total, 4) if total else 0.0

    # Average resolution time for completed items
    resolved_days = [r.get("resolution_days") for r in completed_items if r.get("resolution_days") is not None]
    avg_resolution_days = round(sum(resolved_days) / len(resolved_days), 1) if resolved_days else None

    # By priority
    priority_breakdown: dict[str, dict] = {
        "Critical": {"open": 0, "in_progress": 0, "completed": 0, "overdue": 0},
        "High": {"open": 0, "in_progress": 0, "completed": 0, "overdue": 0},
        "Medium": {"open": 0, "in_progress": 0, "completed": 0, "overdue": 0},
        "Low": {"open": 0, "in_progress": 0, "completed": 0, "overdue": 0},
    }
    for r in recommendations:
        priority = r.get("priority", "Medium")
        pb = priority_breakdown.setdefault(priority, {"open": 0, "in_progress": 0, "completed": 0, "overdue": 0})
        status = r.get("action_status", "open")
        if status in _OPEN_STATUSES:
            pb["open"] += 1
        elif status in _IN_PROGRESS_STATUSES:
            pb["in_progress"] += 1
        elif status in _RESOLVED_STATUSES:
            pb["completed"] += 1
        if r.get("overdue", False) and status not in _RESOLVED_STATUSES:
            pb["overdue"] += 1

    # By supplier
    supplier_counts: dict[str, dict] = {}
    for r in recommendations:
        sid = r.get("supplier_id")
        if not sid:
            continue
        sc = supplier_counts.setdefault(sid, {"open": 0, "overdue": 0, "completed": 0})
        status = r.get("action_status", "open")
        if status in _RESOLVED_STATUSES:
            sc["completed"] += 1
        else:
            sc["open"] += 1
        if r.get("overdue", False) and status not in _RESOLVED_STATUSES:
            sc["overdue"] += 1

    # Top overdue items (sorted by priority desc)
    top_overdue = sorted(
        overdue_items,
        key=lambda x: -_priority_order(x.get("priority", "Medium")),
    )[:10]

    return {
        "meta": {
            "organization_id": organization_id,
            "report_type": "remediation",
        },
        "summary": {
            "total": total,
            "open": len(open_items),
            "in_progress": len(in_progress_items),
            "completed": len(completed_items),
            "overdue": len(overdue_items),
            "closure_rate": closure_rate,
            "avg_resolution_days": avg_resolution_days,
        },
        "by_priority": priority_breakdown,
        "by_supplier": supplier_counts,
        "top_overdue": [
            {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "priority": r.get("priority", "Medium"),
                "action_status": r.get("action_status", "open"),
                "due_date": r.get("due_date", ""),
                "supplier_id": r.get("supplier_id", ""),
            }
            for r in top_overdue
        ],
    }

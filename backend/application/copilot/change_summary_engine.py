"""Change Detection Engine — pure function, no I/O.

Compares a current state snapshot against a previous snapshot and returns
a structured change summary used by the Copilot change questions.
"""

from __future__ import annotations

_RISK_PRIORITY = {"Critical": 4, "High": 3, "Moderate": 2, "Low": 1, "Unknown": 0}


def build_change_summary(
    current: dict,
    previous: dict,
) -> dict:
    """Detect changes between current and previous org state snapshots.

    Both dicts should contain:
      - critical_findings: int
      - critical_risks: int
      - open_recommendations: int
      - risk_distribution: dict[str, int]
      - supplier_critical_count: int
      - compliance_gap_count: int
      - overdue_action_count: int
      - disclosure_weak_count: int

    Returns structured change dict with signed deltas and a severity assessment.
    """
    changes: list[dict] = []

    def _delta(key: str, label: str, higher_is_worse: bool = True) -> None:
        cur = current.get(key, 0) or 0
        prev = previous.get(key, 0) or 0
        diff = cur - prev
        if diff == 0:
            return
        direction = "increased" if diff > 0 else "decreased"
        severity = "critical" if abs(diff) >= 5 else ("warning" if abs(diff) >= 2 else "info")
        if higher_is_worse and diff > 0:
            severity = "critical" if diff >= 5 else "warning"
        elif not higher_is_worse and diff < 0:
            severity = "critical" if abs(diff) >= 5 else "warning"
        else:
            severity = "info"
        changes.append(
            {
                "metric": key,
                "label": label,
                "previous": prev,
                "current": cur,
                "delta": diff,
                "direction": direction,
                "severity": severity,
            }
        )

    _delta("critical_findings", "Critical findings", higher_is_worse=True)
    _delta("critical_risks", "Critical risks", higher_is_worse=True)
    _delta("open_recommendations", "Open recommendations", higher_is_worse=True)
    _delta("supplier_critical_count", "Critical-band suppliers", higher_is_worse=True)
    _delta("compliance_gap_count", "Compliance gaps", higher_is_worse=True)
    _delta("overdue_action_count", "Overdue actions", higher_is_worse=True)
    _delta("disclosure_weak_count", "Weak disclosures", higher_is_worse=True)

    # Risk distribution shift
    cur_dist = current.get("risk_distribution", {})
    prev_dist = previous.get("risk_distribution", {})
    all_bands = set(cur_dist) | set(prev_dist)
    dist_changes = {}
    for band in all_bands:
        diff = (cur_dist.get(band, 0) or 0) - (prev_dist.get(band, 0) or 0)
        if diff != 0:
            dist_changes[band] = diff

    # Compute aggregate severity
    severities = [c["severity"] for c in changes]
    if "critical" in severities:
        overall_severity = "critical"
    elif "warning" in severities:
        overall_severity = "warning"
    else:
        overall_severity = "stable"

    return {
        "overall_severity": overall_severity,
        "changes": changes,
        "risk_distribution_changes": dist_changes,
        "new_concerns": [
            c for c in changes if c["severity"] in ("critical", "warning") and c["delta"] > 0
        ],
        "improvements": [c for c in changes if c["delta"] < 0],
        "total_changes": len(changes),
    }

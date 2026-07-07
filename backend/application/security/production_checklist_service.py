"""M49 — Production Cutover Checklist.

Defines and seeds the complete production readiness checklist for EIOS GA.
Covers infrastructure, security, data, operations, compliance, and testing gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRODUCTION_CHECKLIST: list[dict[str, str]] = [
    # ── Infrastructure ────────────────────────────────────────────────────────
    {
        "category": "Infrastructure",
        "priority": "HIGH",
        "item_name": "SSL/TLS certificates provisioned",
        "description": "Valid TLS cert from trusted CA; auto-renewal configured (Let's Encrypt / ACM).",
    },
    {
        "category": "Infrastructure",
        "priority": "HIGH",
        "item_name": "CDN and WAF active",
        "description": "Cloudflare or AWS CloudFront in front of API; WAF rules for OWASP Top 10.",
    },
    {
        "category": "Infrastructure",
        "priority": "HIGH",
        "item_name": "Database backups configured",
        "description": "Automated nightly snapshots + WAL archiving; retention ≥30 days.",
    },
    {
        "category": "Infrastructure",
        "priority": "HIGH",
        "item_name": "Disaster recovery runbook tested",
        "description": "RTO ≤4h, RPO ≤1h; DR drill completed and documented.",
    },
    {
        "category": "Infrastructure",
        "priority": "HIGH",
        "item_name": "Kubernetes cluster autoscaling enabled",
        "description": "HPA configured for API and Celery workers; node group min/max set.",
    },
    {
        "category": "Infrastructure",
        "priority": "MEDIUM",
        "item_name": "Redis Sentinel or Cluster deployed",
        "description": "Redis high-availability for token blacklist and rate limiter.",
    },
    {
        "category": "Infrastructure",
        "priority": "MEDIUM",
        "item_name": "DDoS protection active",
        "description": "Rate limiting at CDN layer + application rate limiter middleware.",
    },
    {
        "category": "Infrastructure",
        "priority": "LOW",
        "item_name": "Multi-region failover documented",
        "description": "Secondary region runbook; DNS failover via Route53 health checks.",
    },
    # ── Security ──────────────────────────────────────────────────────────────
    {
        "category": "Security",
        "priority": "HIGH",
        "item_name": "Secrets rotation completed",
        "description": "SECRET_KEY, DB credentials, API keys rotated; old secrets invalidated.",
    },
    {
        "category": "Security",
        "priority": "HIGH",
        "item_name": "MFA enforced for all admin accounts",
        "description": "TOTP or hardware key required; no admin login without MFA.",
    },
    {
        "category": "Security",
        "priority": "HIGH",
        "item_name": "Penetration test completed",
        "description": "External pentest against OWASP Top 10; all CRITICAL/HIGH findings remediated.",
    },
    {
        "category": "Security",
        "priority": "HIGH",
        "item_name": "Dependency audit clean",
        "description": "pip-audit shows zero HIGH/CRITICAL CVEs in production dependencies.",
    },
    {
        "category": "Security",
        "priority": "HIGH",
        "item_name": "RBAC roles reviewed",
        "description": "Minimum privilege; production service accounts have no admin roles.",
    },
    {
        "category": "Security",
        "priority": "MEDIUM",
        "item_name": "SOC 2 Type I controls implemented",
        "description": "≥80% of CC/A1/C1 controls marked Implemented with evidence.",
    },
    {
        "category": "Security",
        "priority": "MEDIUM",
        "item_name": "Security headers verified",
        "description": "CSP, HSTS, X-Frame-Options, X-Content-Type-Options present on all responses.",
    },
    {
        "category": "Security",
        "priority": "MEDIUM",
        "item_name": "API rate limiting active",
        "description": "Rate limiter middleware deployed; limits tuned for production traffic.",
    },
    # ── Data ─────────────────────────────────────────────────────────────────
    {
        "category": "Data",
        "priority": "HIGH",
        "item_name": "All Alembic migrations applied",
        "description": "Migration head matches ORM; no pending migrations in production.",
    },
    {
        "category": "Data",
        "priority": "HIGH",
        "item_name": "PII data audit completed",
        "description": "All PII fields identified, documented, and covered by data retention policy.",
    },
    {
        "category": "Data",
        "priority": "HIGH",
        "item_name": "Encryption at rest verified",
        "description": "DB storage encrypted (AES-256); S3 buckets encrypted with KMS.",
    },
    {
        "category": "Data",
        "priority": "HIGH",
        "item_name": "GDPR data processing agreements signed",
        "description": "DPA with all sub-processors (AWS, SendGrid, etc.) in place.",
    },
    {
        "category": "Data",
        "priority": "MEDIUM",
        "item_name": "Data retention policies enforced",
        "description": "Automated purge jobs configured; audit logs retained ≥7 years.",
    },
    {
        "category": "Data",
        "priority": "MEDIUM",
        "item_name": "Seed data validated",
        "description": "Regulatory frameworks, disclosure standards, questionnaire templates verified in prod.",
    },
    # ── Operations ────────────────────────────────────────────────────────────
    {
        "category": "Operations",
        "priority": "HIGH",
        "item_name": "Monitoring dashboards live",
        "description": "Grafana dashboards for API latency, error rate, DB connections, Celery queue depth.",
    },
    {
        "category": "Operations",
        "priority": "HIGH",
        "item_name": "Alerting configured",
        "description": "PagerDuty/OpsGenie alerts for p99 latency >1s, error rate >1%, DB connection exhaustion.",
    },
    {
        "category": "Operations",
        "priority": "HIGH",
        "item_name": "On-call rotation active",
        "description": "24/7 on-call schedule set up; escalation policy defined.",
    },
    {
        "category": "Operations",
        "priority": "HIGH",
        "item_name": "Runbooks documented",
        "description": "Runbooks for: DB failover, Redis outage, Celery worker crash, auth service failure.",
    },
    {
        "category": "Operations",
        "priority": "MEDIUM",
        "item_name": "Log aggregation configured",
        "description": "structlog JSON shipped to Datadog/CloudWatch; retention 90 days.",
    },
    {
        "category": "Operations",
        "priority": "MEDIUM",
        "item_name": "Celery worker health monitoring",
        "description": "Flower or custom health endpoint; dead-letter queue alerting.",
    },
    # ── Compliance ────────────────────────────────────────────────────────────
    {
        "category": "Compliance",
        "priority": "HIGH",
        "item_name": "Privacy policy published",
        "description": "GDPR-compliant privacy policy live on product domain.",
    },
    {
        "category": "Compliance",
        "priority": "HIGH",
        "item_name": "Terms of service published",
        "description": "Enterprise MSA / ToS reviewed by legal and published.",
    },
    {
        "category": "Compliance",
        "priority": "HIGH",
        "item_name": "SOC 2 Type I report initiated",
        "description": "Auditor engaged; evidence collection started; target report date set.",
    },
    {
        "category": "Compliance",
        "priority": "MEDIUM",
        "item_name": "Cookie consent implemented",
        "description": "Cookie banner with opt-in/opt-out for analytics; consent stored.",
    },
    {
        "category": "Compliance",
        "priority": "MEDIUM",
        "item_name": "DSAR process documented",
        "description": "Data Subject Access Request process defined; response within 30 days.",
    },
    # ── Testing ───────────────────────────────────────────────────────────────
    {
        "category": "Testing",
        "priority": "HIGH",
        "item_name": "All 60 gap unit tests passing",
        "description": "CI green on main branch; test coverage ≥80% for application layer.",
    },
    {
        "category": "Testing",
        "priority": "HIGH",
        "item_name": "Load test completed",
        "description": "k6 / Locust test at 2× expected peak load; p99 latency ≤500ms.",
    },
    {
        "category": "Testing",
        "priority": "HIGH",
        "item_name": "End-to-end smoke test suite passing",
        "description": "E2E tests covering auth, assessment, supplier portal, notifications.",
    },
    {
        "category": "Testing",
        "priority": "MEDIUM",
        "item_name": "Mobile browser compatibility verified",
        "description": "UI tested on Chrome, Firefox, Safari (desktop + mobile).",
    },
    {
        "category": "Testing",
        "priority": "MEDIUM",
        "item_name": "Accessibility audit completed",
        "description": "WCAG 2.1 AA audit passed; zero critical a11y violations.",
    },
]


@dataclass
class ChecklistSummary:
    total: int
    complete: int
    pending: int
    na: int
    by_category: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def completion_pct(self) -> float:
        eligible = self.total - self.na
        if eligible == 0:
            return 100.0
        return round((self.complete / eligible) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "complete": self.complete,
            "pending": self.pending,
            "na": self.na,
            "completion_pct": self.completion_pct,
            "ga_ready": self.completion_pct >= 90.0,
            "by_category": self.by_category,
        }


def compute_checklist_summary(items: list[dict[str, Any]]) -> ChecklistSummary:
    """Compute summary statistics from a list of checklist item dicts."""
    total = len(items)
    complete = sum(1 for i in items if i.get("status") == "Complete")
    na = sum(1 for i in items if i.get("status") == "N/A")
    pending = total - complete - na

    by_cat: dict[str, dict[str, Any]] = {}
    for item in items:
        cat = item.get("category", "?")
        if cat not in by_cat:
            by_cat[cat] = {"total": 0, "complete": 0, "pending": 0}
        by_cat[cat]["total"] += 1
        if item.get("status") == "Complete":
            by_cat[cat]["complete"] += 1
        elif item.get("status") == "Pending":
            by_cat[cat]["pending"] += 1

    return ChecklistSummary(
        total=total, complete=complete, pending=pending, na=na, by_category=by_cat
    )

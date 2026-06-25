"""G-046 — Certificate expiry alert Celery task.

Runs daily via Celery Beat. Finds supplier certificates whose expiry date
is within `alert_days_before` days, creates a notification, and stamps
`last_alert_sent_at` to prevent duplicate alerts within the same day.

Design:
  - Never auto-revokes or modifies certificates. Read-only on cert table.
  - Creates Notification records (not emails) — relies on notification fanout.
  - Per-cert cooldown: re-alerts at most once per 20 hours.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="eios.certificates.check_expiry",
    max_retries=2,
    default_retry_delay=300,
)
def check_certificate_expiry_task(self) -> dict[str, object]:
    """Scan upcoming certificate expirations and fire notifications."""
    try:
        return asyncio.run(_run_expiry_check())
    except Exception as exc:
        logger.error("cert_expiry_check_failed", error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_expiry_check() -> dict[str, object]:
    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.models.m46_3 import SupplierCertificateModel  # noqa: PLC0415
    from infrastructure.persistence.models.user import UserModel  # noqa: PLC0415
    from infrastructure.persistence.models.notification import NotificationModel  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    now = datetime.now(UTC)
    alerted = 0
    errors = 0

    async with AsyncSessionFactory() as session, session.begin():
        result = await session.execute(select(SupplierCertificateModel))
        certs = list(result.scalars().all())

        for cert in certs:
            days_until_expiry = (cert.expires_at - now).days
            if days_until_expiry > cert.alert_days_before:
                continue

            # Cooldown: don't re-alert within 20 hours
            if (
                cert.last_alert_sent_at
                and (now - cert.last_alert_sent_at).total_seconds() < 3600 * 20
            ):
                continue

            try:
                is_expired = days_until_expiry < 0
                label = "Expired" if is_expired else "Expiring"
                days_str = (
                    f"expired {abs(days_until_expiry)}d ago"
                    if is_expired
                    else f"expires in {days_until_expiry}d"
                )
                title = f"Certificate {label}: {cert.name}"
                body = f"{cert.cert_type} certificate for supplier {cert.supplier_id} — {days_str}."

                # Create one notification per admin user in the org
                admin_result = await session.execute(
                    select(UserModel).where(
                        UserModel.organization_id == cert.organization_id,
                        UserModel.role.in_(["Admin", "SuperAdmin"]),
                        UserModel.status == "Active",
                    )
                )
                admins = list(admin_result.scalars().all())

                for admin in admins:
                    dedupe = f"cert_expiry:{cert.id}:{admin.id}:{now.date().isoformat()}"
                    notification = NotificationModel(
                        id=str(uuid.uuid4()),
                        status="Active",
                        version=1,
                        owner=None,
                        created_by="system:cert_expiry",
                        updated_by="system:cert_expiry",
                        created_at=now,
                        updated_at=now,
                        organization_id=cert.organization_id,
                        user_id=admin.id,
                        notification_type="certificate_expiry",
                        title=title,
                        body=body,
                        entity_type="supplier_certificate",
                        entity_id=cert.id,
                        is_read=False,
                        dedupe_key=dedupe,
                    )
                    session.add(notification)

                cert.last_alert_sent_at = now
                cert.updated_at = now
                alerted += 1

                logger.info(
                    "cert_expiry_alert",
                    cert_id=cert.id,
                    supplier_id=cert.supplier_id,
                    days_until_expiry=days_until_expiry,
                    admins_notified=len(admins),
                )
            except Exception as exc:
                logger.error("cert_expiry_error", cert_id=cert.id, error=str(exc))
                errors += 1

    return {"alerted": alerted, "errors": errors, "checked_at": now.isoformat()}

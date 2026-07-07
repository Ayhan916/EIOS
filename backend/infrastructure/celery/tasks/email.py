"""Email Celery task (M46.2 — G-009 supplier invitation flow).

Sends transactional emails via SMTP. Gracefully skips when smtp_host is empty.
Uses --pool=solo asyncio pattern consistent with other EIOS Celery tasks.
"""

from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    name="eios.email.send",
    max_retries=3,
    default_retry_delay=60,
)
def send_email_task(
    self,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> dict[str, object]:
    """Send a transactional email.

    Returns {"status": "sent"} or {"status": "skipped"} when SMTP is not configured.
    Retries up to 3 times on SMTP errors.
    """
    from shared.config import settings  # noqa: PLC0415

    if not settings.smtp_host:
        logger.info("email_skipped_no_smtp", to=to_email, subject=subject)
        return {"status": "skipped", "reason": "smtp_not_configured"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if settings.smtp_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(settings.smtp_from, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(settings.smtp_from, to_email, msg.as_string())

        logger.info("email_sent", to=to_email, subject=subject)
        return {"status": "sent", "to": to_email}

    except smtplib.SMTPException as exc:
        logger.error("email_send_failed", to=to_email, error=str(exc))
        raise self.retry(exc=exc) from exc


def send_supplier_invitation_email(
    *,
    to_email: str,
    supplier_name: str,
    organization_name: str,
    invite_url: str,
) -> None:
    """Queue an invitation email for a supplier user."""
    html_body = f"""
    <html><body>
    <h2>You've been invited to EIOS</h2>
    <p>You have been invited to access the EIOS supplier portal for <strong>{supplier_name}</strong>
    by <strong>{organization_name}</strong>.</p>
    <p><a href="{invite_url}" style="background:#2563EB;color:#fff;padding:12px 24px;border-radius:4px;text-decoration:none;">
    Accept Invitation</a></p>
    <p>This link expires in 72 hours.</p>
    <p>If you did not expect this invitation, you can safely ignore this email.</p>
    </body></html>
    """
    text_body = (
        f"You've been invited to the EIOS supplier portal for {supplier_name} "
        f"by {organization_name}.\n\nAccept here: {invite_url}\n\n"
        "This link expires in 72 hours."
    )
    send_email_task.delay(
        to_email=to_email,
        subject=f"Invitation to EIOS Supplier Portal — {supplier_name}",
        html_body=html_body,
        text_body=text_body,
    )

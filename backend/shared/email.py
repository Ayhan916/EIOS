"""
EIOS Email Sender

Wraps stdlib smtplib in asyncio.to_thread so the async app doesn't block.
Email is silently skipped when SMTP_HOST is not configured.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from shared.config import settings

logger = structlog.get_logger(__name__)


def _send_sync(to: str, subject: str, body_html: str, body_text: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.smtp_from, [to], msg.as_string())


async def send_email(to: str, subject: str, body_html: str, body_text: str = "") -> None:
    """Send an email. No-op when SMTP is not configured."""
    if not settings.email_enabled:
        return
    if not body_text:
        body_text = body_html
    try:
        await asyncio.to_thread(_send_sync, to, subject, body_html, body_text)
        logger.info("email_sent", to=to, subject=subject)
    except Exception as exc:
        logger.error("email_send_failed", to=to, subject=subject, error=str(exc))

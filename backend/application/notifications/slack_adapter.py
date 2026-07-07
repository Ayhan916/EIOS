"""M48.1 G-022 — Slack Notification Adapter.

Sends Block Kit messages to a Slack Incoming Webhook URL.
Config: SLACK_WEBHOOK_URL per organization (stored in notification_preferences).

Docs: https://api.slack.com/messaging/webhooks
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0

_SEVERITY_EMOJI: dict[str, str] = {
    "CRITICAL": ":red_circle:",
    "HIGH": ":orange_circle:",
    "MEDIUM": ":yellow_circle:",
    "LOW": ":large_blue_circle:",
}


def _mask_url(url: str) -> str:
    h = hashlib.sha256(url.encode()).hexdigest()[:8]
    return f"slack-webhook:{h}"


def build_block_kit_message(
    *,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    severity: str | None = None,
    action_url: str | None = None,
) -> dict[str, Any]:
    """Build a Slack Block Kit message payload."""
    emoji = _SEVERITY_EMOJI.get(severity or "", ":bell:")
    header_text = f"{emoji} *{title}*"

    blocks: list[dict] = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": body},
        },
    ]

    fields = []
    if entity_type:
        fields.append(
            {"type": "mrkdwn", "text": f"*Type*\n{entity_type.replace('_', ' ').title()}"}
        )
    if severity:
        fields.append({"type": "mrkdwn", "text": f"*Severity*\n{severity}"})
    if entity_id:
        fields.append({"type": "mrkdwn", "text": f"*ID*\n`{entity_id[:16]}`"})

    if fields:
        blocks.append({"type": "section", "fields": fields})

    if action_url:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View in EIOS"},
                        "url": action_url,
                        "action_id": "view_in_eios",
                    }
                ],
            }
        )

    blocks.append({"type": "divider"})

    return {"blocks": blocks}


async def send_slack_notification(
    *,
    webhook_url: str,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    severity: str | None = None,
    action_url: str | None = None,
) -> bool:
    """POST a Block Kit message to a Slack webhook.

    Returns True on success, False on failure (non-raising).
    """
    if not webhook_url or not webhook_url.startswith("https://hooks.slack.com/"):
        logger.warning("slack_adapter: invalid webhook URL skipped")
        return False

    payload = build_block_kit_message(
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        action_url=action_url,
    )

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info("slack_notification_sent", webhook=_mask_url(webhook_url))
            return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "slack_notification_failed",
            webhook=_mask_url(webhook_url),
            status=exc.response.status_code,
        )
        return False
    except Exception as exc:
        logger.error(
            "slack_notification_error",
            webhook=_mask_url(webhook_url),
            error=str(exc),
        )
        return False

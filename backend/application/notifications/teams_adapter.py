"""M48.1 G-022 — Microsoft Teams Notification Adapter.

Sends Adaptive Cards to a Teams Incoming Webhook URL.
Config: TEAMS_WEBHOOK_URL per organization (stored in notification_preferences).

Security: webhook URL is treated as a secret — never logged in full.
Docs: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


def _mask_url(url: str) -> str:
    """Return a safe log-safe representation of a webhook URL."""
    h = hashlib.sha256(url.encode()).hexdigest()[:8]
    return f"teams-webhook:{h}"


def build_adaptive_card(
    *,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    severity: str | None = None,
    action_url: str | None = None,
) -> dict[str, Any]:
    """Build a minimal Teams Adaptive Card payload."""
    facts = []
    if entity_type:
        facts.append({"title": "Type", "value": entity_type.replace("_", " ").title()})
    if entity_id:
        facts.append({"title": "ID", "value": entity_id[:16]})
    if severity:
        facts.append({"title": "Severity", "value": severity})

    card_body: list[dict] = [
        {
            "type": "TextBlock",
            "size": "Medium",
            "weight": "Bolder",
            "text": title,
            "wrap": True,
        },
        {
            "type": "TextBlock",
            "text": body,
            "wrap": True,
            "isSubtle": True,
        },
    ]

    if facts:
        card_body.append({
            "type": "FactSet",
            "facts": facts,
        })

    actions = []
    if action_url:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "View in EIOS",
            "url": action_url,
        })

    payload: dict[str, Any] = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": card_body,
                    "actions": actions,
                    "msteams": {"width": "Full"},
                },
            }
        ],
    }
    return payload


async def send_teams_notification(
    *,
    webhook_url: str,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    severity: str | None = None,
    action_url: str | None = None,
) -> bool:
    """POST an Adaptive Card to a Teams webhook.

    Returns True on success, False on failure (non-raising — caller decides escalation).
    """
    if not webhook_url or not webhook_url.startswith("https://"):
        logger.warning("teams_adapter: invalid webhook URL skipped")
        return False

    payload = build_adaptive_card(
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
            logger.info("teams_notification_sent", webhook=_mask_url(webhook_url))
            return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "teams_notification_failed",
            webhook=_mask_url(webhook_url),
            status=exc.response.status_code,
        )
        return False
    except Exception as exc:
        logger.error(
            "teams_notification_error",
            webhook=_mask_url(webhook_url),
            error=str(exc),
        )
        return False

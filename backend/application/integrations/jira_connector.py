"""M48.1 G-047 — JIRA + ServiceNow Connector.

Creates tickets from EIOS Findings via external issue tracking APIs.
Stores resulting ticket URL on the Finding (external_ticket_url column).

JIRA REST API v3: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
ServiceNow REST: https://docs.servicenow.com/en-US/bundle/washingtondc-api-reference/page/integrate/inbound-rest/concept/c_TableAPI.html
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0

TicketSystem = Literal["jira", "servicenow"]


@dataclass
class TicketResult:
    ticket_url: str
    ticket_id: str
    system: TicketSystem


async def create_jira_ticket(
    *,
    base_url: str,
    email: str,
    api_token: str,
    project_key: str,
    issue_type: str = "Bug",
    priority: str = "Medium",
    summary: str,
    description: str,
    labels: list[str] | None = None,
) -> TicketResult:
    """Create a JIRA issue via REST API v3.

    Args:
        base_url: e.g. "https://your-org.atlassian.net"
        email / api_token: Basic-auth credentials
        project_key: JIRA project key (e.g. "ESG")
        summary / description: Issue content

    Returns:
        TicketResult with URL and issue key.

    Raises:
        httpx.HTTPStatusError on 4xx/5xx from JIRA.
    """
    url = f"{base_url.rstrip('/')}/rest/api/3/issue"
    payload: dict[str, Any] = {
        "fields": {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary[:255],
            "priority": {"name": priority},
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description[:10000]}],
                    }
                ],
            },
            **({"labels": labels} if labels else {}),
        }
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            url,
            json=payload,
            auth=(email, api_token),
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

    issue_key = data["key"]
    ticket_url = f"{base_url.rstrip('/')}/browse/{issue_key}"
    logger.info("jira_ticket_created", issue_key=issue_key)
    return TicketResult(ticket_url=ticket_url, ticket_id=issue_key, system="jira")


async def create_servicenow_ticket(
    *,
    instance_url: str,
    username: str,
    password: str,
    table: str = "incident",
    short_description: str,
    description: str,
    urgency: str = "2",
    impact: str = "2",
) -> TicketResult:
    """Create a ServiceNow record via Table API.

    Args:
        instance_url: e.g. "https://dev12345.service-now.com"
        table: ServiceNow table (incident | change_request | problem)
        urgency / impact: 1=High, 2=Medium, 3=Low

    Returns:
        TicketResult with URL and sys_id.
    """
    url = f"{instance_url.rstrip('/')}/api/now/table/{table}"
    payload = {
        "short_description": short_description[:160],
        "description": description[:4000],
        "urgency": urgency,
        "impact": impact,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            url,
            json=payload,
            auth=(username, password),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()["result"]

    sys_id = data["sys_id"]
    ticket_url = f"{instance_url.rstrip('/')}/nav_to.do?uri={table}.do?sys_id={sys_id}"
    logger.info("servicenow_ticket_created", sys_id=sys_id, table=table)
    return TicketResult(ticket_url=ticket_url, ticket_id=sys_id, system="servicenow")

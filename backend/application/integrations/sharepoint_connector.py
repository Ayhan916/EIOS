"""M48.1 G-049 — SharePoint Evidence Connector.

Imports documents from SharePoint via Microsoft Graph API into EIOS Evidence.

OAuth2 flow (delegated):
  1. User redirected to /api/v1/integrations/sharepoint/auth
  2. Microsoft returns code to /api/v1/integrations/sharepoint/callback
  3. Tokens stored encrypted in org settings
  4. POST /api/v1/evidence/import-sharepoint fetches file and creates Evidence

Security: Access tokens are short-lived (1h). Refresh tokens stored per org.
Scopes required: Files.Read.All, Sites.Read.All
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TIMEOUT = 30.0
_AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_SCOPES = "Files.Read.All Sites.Read.All offline_access"


def build_auth_url(
    *,
    tenant_id: str,
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Return the Microsoft OAuth2 authorization URL for the user redirect."""
    base = _AUTH_URL.format(tenant_id=tenant_id)
    params = (
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope={_SCOPES.replace(' ', '%20')}"
        f"&state={state}"
        f"&response_mode=query"
    )
    return base + params


async def exchange_code_for_tokens(
    *,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange auth code for access + refresh tokens.

    Returns raw Microsoft token response dict.
    """
    url = _TOKEN_URL.format(tenant_id=tenant_id)
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "scope": _SCOPES,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        return response.json()


async def list_sharepoint_files(
    *,
    access_token: str,
    site_id: str,
    drive_id: str | None = None,
    folder_path: str = "root",
) -> list[dict[str, Any]]:
    """List files in a SharePoint drive folder.

    Returns list of {id, name, size, webUrl, mimeType, lastModified}.
    """
    if drive_id:
        url = f"{_GRAPH_BASE}/sites/{site_id}/drives/{drive_id}/root/children"
    else:
        url = f"{_GRAPH_BASE}/sites/{site_id}/drive/root/children"

    headers = {"Authorization": f"Bearer {access_token}"}
    items = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        while url:
            res = await client.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()
            for item in data.get("value", []):
                if "file" in item:
                    items.append(
                        {
                            "id": item["id"],
                            "name": item["name"],
                            "size": item.get("size", 0),
                            "webUrl": item.get("webUrl", ""),
                            "mimeType": item["file"].get("mimeType", ""),
                            "lastModified": item.get("lastModifiedDateTime", ""),
                        }
                    )
            url = data.get("@odata.nextLink")

    return items


async def download_sharepoint_file(
    *,
    access_token: str,
    site_id: str,
    item_id: str,
) -> bytes:
    """Download file content bytes from SharePoint."""
    url = f"{_GRAPH_BASE}/sites/{site_id}/drive/items/{item_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        res = await client.get(url, headers=headers)
        res.raise_for_status()
        return res.content

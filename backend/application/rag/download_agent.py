"""Download Agent — fetcht PDF/HTML von einer URL.

Features:
  - Retry mit exponential backoff
  - Content-Type-Erkennung (PDF vs HTML)
  - User-Agent rotation
  - Max-Size-Guard (100 MB)
  - Timeout: 30s connect, 120s read
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

_MAX_BYTES = 100 * 1024 * 1024  # 100 MB
_USER_AGENTS = [
    "Mozilla/5.0 (compatible; EIOSBot/1.0; +https://eios.app/bot)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


@dataclass
class DownloadResult:
    ok: bool
    content: bytes | None = None
    content_type: str | None = None  # "pdf" | "html" | "text"
    final_url: str | None = None
    error: str | None = None


async def download(url: str, max_retries: int = 3) -> DownloadResult:
    """Download a document from a URL. Returns DownloadResult."""
    try:
        import httpx
    except ImportError:
        return DownloadResult(ok=False, error="httpx not installed — run: pip install httpx")

    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "application/pdf,text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }

    last_error: str = ""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0),
                headers=headers,
            ) as client:
                async with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    final_url = str(resp.url)
                    ct = resp.headers.get("content-type", "").lower()

                    # Determine type
                    if "pdf" in ct or url.lower().endswith(".pdf"):
                        content_type = "pdf"
                    elif "html" in ct:
                        content_type = "html"
                    else:
                        content_type = "text"

                    # Stream with size guard
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        size += len(chunk)
                        if size > _MAX_BYTES:
                            return DownloadResult(ok=False, error=f"File too large (>{_MAX_BYTES // 1024 // 1024} MB)")
                        chunks.append(chunk)

                    content = b"".join(chunks)
                    logger.info("download_agent.done", url=url, size=size, type=content_type)
                    return DownloadResult(
                        ok=True,
                        content=content,
                        content_type=content_type,
                        final_url=final_url,
                    )

        except Exception as exc:
            last_error = str(exc)
            logger.warning("download_agent.retry", url=url, attempt=attempt, error=last_error)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

    return DownloadResult(ok=False, error=f"Failed after {max_retries} attempts: {last_error}")

"""
Request Body Size Limit Middleware

Rejects requests whose Content-Length exceeds the configured maximum before
the body is read. Complements the per-endpoint file-size check in the evidence
upload route by protecting all other POST/PUT endpoints from oversized payloads.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from shared.config import settings

_MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": (
                        f"Request body exceeds the maximum allowed size "
                        f"of {settings.max_upload_size_mb} MB"
                    )
                },
            )
        return await call_next(request)

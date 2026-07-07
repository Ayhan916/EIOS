"""S3 / MinIO object storage client (M45.2).

Uses boto3 (sync) wrapped in asyncio.to_thread() so FastAPI async endpoints
never block the event loop on S3 network calls.

Configuration (via Settings):
  S3_ENABLED=true
  S3_BUCKET=eios-documents
  S3_REGION=us-east-1
  S3_ENDPOINT_URL=http://minio:9000   # MinIO in dev; empty = AWS in prod
  AWS_ACCESS_KEY_ID=...               # empty = IAM instance profile
  AWS_SECRET_ACCESS_KEY=...

Key format: {org_id}/evidences/{evidence_id}/{uuid4}-{filename}
  This ensures cross-org isolation at the S3 prefix level (defence-in-depth)
  even though primary isolation is via IAM bucket policy + RLS.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _get_client() -> Any:
    import boto3  # noqa: PLC0415

    from shared.config import settings  # noqa: PLC0415

    kwargs: dict[str, Any] = {"region_name": settings.s3_region}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def _upload_sync(content: bytes, key: str, content_type: str) -> None:
    from shared.config import settings  # noqa: PLC0415

    _get_client().put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )


def _download_sync(key: str) -> bytes:
    from shared.config import settings  # noqa: PLC0415

    resp = _get_client().get_object(Bucket=settings.s3_bucket, Key=key)
    return resp["Body"].read()


def _delete_sync(key: str) -> None:
    from shared.config import settings  # noqa: PLC0415

    _get_client().delete_object(Bucket=settings.s3_bucket, Key=key)


def _presign_sync(key: str, expires_in: int) -> str:
    from shared.config import settings  # noqa: PLC0415

    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def _ensure_bucket_sync() -> None:
    """Create the bucket if it doesn't exist (dev/MinIO helper)."""
    from shared.config import settings  # noqa: PLC0415

    client = _get_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception:  # noqa: BLE001
        try:
            if settings.s3_region == "us-east-1":
                client.create_bucket(Bucket=settings.s3_bucket)
            else:
                client.create_bucket(
                    Bucket=settings.s3_bucket,
                    CreateBucketConfiguration={"LocationConstraint": settings.s3_region},
                )
            logger.info("s3_bucket_created", bucket=settings.s3_bucket)
        except Exception as exc2:  # noqa: BLE001
            logger.warning("s3_bucket_create_failed", error=str(exc2))


async def ensure_bucket() -> None:
    await asyncio.to_thread(_ensure_bucket_sync)


async def upload_file(content: bytes, key: str, content_type: str) -> str:
    """Upload bytes to S3.  Returns the key on success."""
    await asyncio.to_thread(_upload_sync, content, key, content_type)
    logger.info("s3_upload_ok", key=key, size=len(content))
    return key


async def download_file(key: str) -> bytes:
    """Download and return bytes from S3."""
    data = await asyncio.to_thread(_download_sync, key)
    logger.info("s3_download_ok", key=key, size=len(data))
    return data


async def delete_file(key: str) -> None:
    """Delete a file from S3 (fire-and-forget on error)."""
    try:
        await asyncio.to_thread(_delete_sync, key)
        logger.info("s3_delete_ok", key=key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("s3_delete_failed", key=key, error=str(exc))


async def generate_presigned_url(key: str, expires_in: int | None = None) -> str:
    """Generate a time-limited presigned GET URL for the given object key."""
    from shared.config import settings  # noqa: PLC0415

    ttl = expires_in or settings.s3_presigned_url_expire_seconds
    return await asyncio.to_thread(_presign_sync, key, ttl)

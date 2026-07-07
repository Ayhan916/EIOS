"""Bulk supplier CSV import Celery task (M46.2 — G-008).

Flow:
  1. FastAPI endpoint parses CSV; ≤100 rows → sync result; >100 rows → dispatches this task.
  2. Task processes rows in batches, deduplicates by name+org, skips duplicates.
  3. Result stored in Celery result backend; client polls GET /suppliers/bulk-import/{task_id}.

CSV columns (header row required):
  name, legal_name, country, industry, nace_code, website, supplier_tier, notes
  Only `name` is mandatory; all others default to empty / Tier 1.
"""

from __future__ import annotations

import asyncio
import csv
import io

import structlog

from infrastructure.celery.app import celery_app

logger = structlog.get_logger(__name__)

_VALID_TIERS = {"Tier 1", "Tier 2", "Tier 3"}
_BATCH_SIZE = 50


@celery_app.task(
    bind=True,
    name="eios.bulk_import.suppliers",
    max_retries=2,
    default_retry_delay=30,
)
def bulk_import_suppliers_task(
    self,
    csv_content: str,
    organization_id: str,
    actor_id: str,
    dry_run: bool = False,
) -> dict[str, object]:
    """Process CSV and upsert supplier rows.

    Returns a summary dict:
      {"imported": int, "skipped": int, "errors": list[dict], "dry_run": bool}
    """
    try:
        return asyncio.run(
            _run_bulk_import(
                csv_content=csv_content,
                organization_id=organization_id,
                actor_id=actor_id,
                dry_run=dry_run,
            )
        )
    except Exception as exc:
        logger.error("bulk_import_failed", organization_id=organization_id, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_bulk_import(
    *,
    csv_content: str,
    organization_id: str,
    actor_id: str,
    dry_run: bool,
) -> dict[str, object]:
    import uuid  # noqa: PLC0415
    from datetime import UTC, datetime  # noqa: PLC0415

    from sqlalchemy import select  # noqa: PLC0415

    from infrastructure.persistence.database import AsyncSessionFactory  # noqa: PLC0415
    from infrastructure.persistence.models.supplier import SupplierModel  # noqa: PLC0415

    rows = _parse_csv(csv_content)
    imported = 0
    skipped = 0
    errors: list[dict] = []

    async with AsyncSessionFactory() as session, session.begin():
        for batch_start in range(0, len(rows), _BATCH_SIZE):
            batch = rows[batch_start : batch_start + _BATCH_SIZE]
            for row_num, row in batch:
                name = row.get("name", "").strip()
                if not name:
                    errors.append({"row": row_num, "error": "name is required"})
                    continue

                supplier_tier = row.get("supplier_tier", "Tier 1").strip() or "Tier 1"
                if supplier_tier not in _VALID_TIERS:
                    errors.append(
                        {"row": row_num, "error": f"invalid supplier_tier: {supplier_tier!r}"}
                    )
                    continue

                # Check for existing supplier with same name in org
                existing = await session.execute(
                    select(SupplierModel)
                    .where(
                        SupplierModel.organization_id == organization_id,
                        SupplierModel.name == name,
                        SupplierModel.status != "Deleted",
                    )
                    .limit(1)
                )
                if existing.scalar_one_or_none() is not None:
                    skipped += 1
                    logger.debug("bulk_import_skip_duplicate", name=name, row=row_num)
                    continue

                if not dry_run:
                    now = datetime.now(UTC)
                    session.add(
                        SupplierModel(
                            id=str(uuid.uuid4()),
                            status="Active",
                            version=1,
                            owner=None,
                            created_by=actor_id,
                            updated_by=actor_id,
                            created_at=now,
                            updated_at=now,
                            organization_id=organization_id,
                            name=name,
                            legal_name=row.get("legal_name", "").strip() or None,
                            country=row.get("country", "").strip(),
                            industry=row.get("industry", "").strip(),
                            nace_code=row.get("nace_code", "").strip() or None,
                            website=row.get("website", "").strip() or None,
                            supplier_tier=supplier_tier,
                            supplier_status="Active",
                            notes=row.get("notes", "").strip() or None,
                        )
                    )
                imported += 1

    logger.info(
        "bulk_import_complete",
        organization_id=organization_id,
        imported=imported,
        skipped=skipped,
        errors=len(errors),
        dry_run=dry_run,
    )
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "dry_run": dry_run,
        "total_rows": len(rows),
    }


def _parse_csv(content: str) -> list[tuple[int, dict[str, str]]]:
    """Parse CSV content and return list of (row_number, row_dict) tuples."""
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for i, row in enumerate(reader, start=2):  # row 1 is header
        # Normalize keys to lowercase, strip whitespace
        normalized = {k.strip().lower(): v for k, v in row.items() if k}
        rows.append((i, normalized))
    return rows


def process_csv_sync(
    csv_content: str,
    organization_id: str,
    actor_id: str,
    dry_run: bool = False,
) -> dict[str, object]:
    """Run bulk import synchronously (for ≤100 rows in request-response path)."""
    return asyncio.run(
        _run_bulk_import(
            csv_content=csv_content,
            organization_id=organization_id,
            actor_id=actor_id,
            dry_run=dry_run,
        )
    )

"""M47 — Region-aware Celery task dispatch helper.

Usage:
    from infrastructure.celery.region_dispatch import dispatch_to_region

    dispatch_to_region(
        bulk_import_suppliers_task,
        args=[csv_content, org_id, actor_id],
        kwargs={},
        region=organization.data_residency,
    )

The task is queued on the regional Celery queue so a worker in the same
region picks it up, keeping data processing within the declared residency.
"""

from __future__ import annotations

from celery import Task

from infrastructure.routing.region_router import region_router


def dispatch_to_region(
    task: Task,
    *,
    region: str | None,
    args: list | None = None,
    kwargs: dict | None = None,
    **apply_async_kwargs,
) -> object:
    """Send `task` to the regional Celery queue for `region`.

    Falls back to the default queue when region is None or unrecognised.
    Returns the AsyncResult from apply_async.
    """
    queue = region_router.get_celery_queue(region)
    return task.apply_async(args=args or [], kwargs=kwargs or {}, queue=queue, **apply_async_kwargs)

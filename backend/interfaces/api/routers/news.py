"""News Feed API — live supplier/country/partner news with translation."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from domain.user import User
from interfaces.api.deps import get_current_user, get_db

router = APIRouter(prefix="/news", tags=["news"])


def _assert_org(user: User) -> str:
    if not user.organization_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="No organisation assigned.")
    return user.organization_id


@router.get("/feed")
async def get_news_feed(
    match_type: str | None = Query(None, description="Filter: supplier | country | partner"),
    supplier_id: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from application.news_feed.news_service import get_news_feed as _get_feed, get_last_refresh
    org_id = _assert_org(current_user)
    articles, total = await _get_feed(
        organization_id=org_id,
        session=session,
        match_type=match_type,
        supplier_id=supplier_id,
        limit=limit,
        offset=offset,
    )
    last_refresh = await get_last_refresh(org_id, session)
    return {
        "articles": articles,
        "total": total,
        "limit": limit,
        "offset": offset,
        "last_refresh": last_refresh.isoformat() if last_refresh else None,
    }


@router.post("/refresh")
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    ui_language: str = Query("de", description="Target language for translation: de | en"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a manual news refresh in the background."""
    from application.news_feed.news_service import refresh_news_for_org
    org_id = _assert_org(current_user)

    async def _run() -> None:
        from infrastructure.persistence.database import AsyncSessionFactory
        async with AsyncSessionFactory() as bg_session:
            await refresh_news_for_org(
                organization_id=org_id,
                session=bg_session,
                ui_language=ui_language,
            )

    background_tasks.add_task(_run)
    return {"status": "refresh_started"}

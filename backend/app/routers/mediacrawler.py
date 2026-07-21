"""
MediaCrawler router — search and import videos via MediaCrawler API.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.mediacrawler_service import (
    search_and_import_videos,
    get_video_detail_and_import,
)

router = APIRouter(prefix="/api/mediacrawler", tags=["mediacrawler"])


@router.post("/search-and-import")
async def search_and_import(
    platform: str = Query(..., description="douyin or kuaishou"),
    keyword: str = Query(..., description="search keyword"),
    limit: int = Query(20, ge=1, le=100),
    sort_type: str = Query("0", description="0=comprehensive, 1=latest, 2=most liked"),
    publish_time: str = Query("0", description="0=all, 1=24h, 7=week, 180=6months"),
    db: AsyncSession = Depends(get_db),
):
    """Search videos via MediaCrawler and import all results."""
    if platform not in ("douyin", "kuaishou"):
        raise HTTPException(status_code=400, detail="platform must be douyin or kuaishou")

    result = await search_and_import_videos(
        db=db,
        platform=platform,
        keyword=keyword,
        limit=limit,
        sort_type=sort_type,
        publish_time=publish_time,
    )
    return result


@router.post("/detail-and-import")
async def detail_and_import(
    platform: str = Query(...),
    video_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Get single video detail via MediaCrawler and import."""
    result = await get_video_detail_and_import(
        db=db, platform=platform, video_id=video_id,
    )
    return result

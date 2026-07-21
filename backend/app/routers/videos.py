"""
Video router — CRUD, list, field updates with audit.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    VideoCreate, VideoUpdate, VideoResponse, VideoListResponse,
    MetricSnapshotCreate, MetricSnapshotResponse, BrowserExtractImport,
    SingleLinkImport, ImportResultResponse,
)
from app.services.video_service import (
    create_video, get_video_by_id, get_video_with_author,
    list_videos, update_video_field, bulk_update_video_fields,
    create_metric_snapshot, get_video_snapshots,
)
from app.services.import_service import (
    import_single_link, parse_row_to_video_data,
)
from app.adapters.browser_extract import BrowserExtractAdapter
from app.utils.hashing import hash_author_id

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("", response_model=VideoListResponse)
async def list_videos_handler(
    platform: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None),
    collection_method: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    sort_desc: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """List videos with filtering, sorting, and pagination."""
    videos, total = await list_videos(
        db=db,
        platform=platform,
        verification_status=verification_status,
        collection_method=collection_method,
        keyword=keyword,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )
    return VideoListResponse(
        videos=[_to_response(v) for v in videos],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single video by ID."""
    video = await get_video_with_author(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return _to_response(video)


@router.post("/single-link", response_model=dict)
async def import_single_link_handler(
    data: SingleLinkImport,
    db: AsyncSession = Depends(get_db),
):
    """Import a single video from a pasted URL."""
    video_id, error = await import_single_link(
        db=db, url=data.url, metadata=data.metadata,
    )
    if error:
        return {"success": False, "video_id": video_id, "error": error}
    return {"success": True, "video_id": video_id, "error": None}


@router.post("/browser-extract", response_model=dict)
async def import_browser_extract(
    data: BrowserExtractImport,
    db: AsyncSession = Depends(get_db),
):
    """Import video data from browser page extraction JSON."""
    adapter = BrowserExtractAdapter()
    result = await adapter.extract(data.json_data)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.errors)

    # Create video
    from app.services.video_service import create_video as svc_create

    author_id_hash = result.author_data.get("author_id_hash") if result.author_data else None
    author_data = result.author_data.copy() if result.author_data else {}
    author_data.pop("author_id_hash", None)

    video, is_new = await svc_create(
        db=db,
        video_data=result.video_data,
        author_data=author_data,
        author_id_hash=author_id_hash,
    )

    # Create metric snapshot
    snapshot = None
    if result.metric_data:
        snapshot = await create_metric_snapshot(
            db=db, video_id=video.id, metrics=result.metric_data,
            collection_method="researcher_browser",
        )

    # Create comments
    comments_imported = 0
    if result.comments_data:
        for c in result.comments_data:
            from app.models.comment import Comment
            comment = Comment(
                video_id=video.id,
                comment_id_hash=c["comment_id_hash"],
                comment_text=c["comment_text"],
                comment_time=c["comment_time"],
                like_count=c["like_count"],
                reply_count=c["reply_count"],
                comment_rank=c["comment_rank"],
                sort_mode=c["sort_mode"],
                parent_comment_id_hash=c["parent_comment_id_hash"],
                commenter_id_hash=c["commenter_id_hash"],
                self_disclosed_age=c["self_disclosed_age"],
                collected_at=result.video_data.get("first_collected_at"),
            )
            db.add(comment)
            comments_imported += 1
        await db.commit()

    return {
        "success": True,
        "video_id": video.id,
        "is_new": is_new,
        "snapshot_id": snapshot.id if snapshot else None,
        "comments_imported": comments_imported,
        "warnings": result.warnings,
    }


@router.patch("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: str,
    data: VideoUpdate,
    modified_by: str = Query("system"),
    db: AsyncSession = Depends(get_db),
):
    """Update video fields with audit logging."""
    updates = data.model_dump(exclude_unset=True, exclude_none=True)
    change_reason = updates.pop("change_reason", None)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    video = await bulk_update_video_fields(
        db=db,
        video_id=video_id,
        updates=updates,
        modified_by=modified_by,
        change_reason=change_reason,
    )

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return _to_response(video)


@router.get("/{video_id}/snapshots", response_model=List[MetricSnapshotResponse])
async def list_snapshots(video_id: str, db: AsyncSession = Depends(get_db)):
    """Get all metric snapshots for a video."""
    snapshots = await get_video_snapshots(db, video_id)
    return [MetricSnapshotResponse.model_validate(s) for s in snapshots]


@router.post("/{video_id}/snapshots", response_model=MetricSnapshotResponse)
async def add_snapshot(
    video_id: str,
    data: MetricSnapshotCreate,
    collector_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new metric snapshot for a video."""
    video = await get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    snapshot = await create_metric_snapshot(
        db=db,
        video_id=video_id,
        metrics=data.model_dump(exclude_none=True),
        collector_id=collector_id,
        collection_method="manual",
    )
    return MetricSnapshotResponse.model_validate(snapshot)


def _to_response(video) -> VideoResponse:
    """Convert Video ORM object to VideoResponse."""
    # Get latest snapshot metrics (safe — returns None if not loaded)
    latest_like = None
    latest_comment = None
    latest_share = None
    latest_view = None
    latest_at = None
    try:
        snaps = video.metric_snapshots
        if snaps:
            latest = snaps[-1]
            latest_like = latest.like_count
            latest_comment = latest.comment_count
            latest_share = latest.share_count
            latest_view = latest.view_count
            latest_at = latest.collected_at
    except Exception:
        pass

    # Author fields (safe)
    author_name = None
    follower_count = None
    account_verified = None
    try:
        if video.author:
            author_name = video.author.author_name_public
            follower_count = video.author.follower_count
            account_verified = video.author.account_verified
    except Exception:
        pass

    return VideoResponse(
        id=video.id,
        platform=video.platform,
        platform_video_id=video.platform_video_id,
        video_url=video.video_url,
        short_url=video.short_url,
        video_title=video.video_title,
        hashtags=video.hashtags,
        publish_time=video.publish_time,
        duration_seconds=video.duration_seconds,
        cover_url=video.cover_url,
        collection_method=video.collection_method,
        data_source=video.data_source,
        verification_status=video.verification_status,
        collection_keyword=video.collection_keyword,
        search_result_rank=video.search_result_rank,
        first_collected_at=video.first_collected_at,
        public_at_collection=video.public_at_collection,
        available_at_followup=video.available_at_followup,
        unavailable_reason=video.unavailable_reason,
        author_name=author_name,
        follower_count=follower_count,
        account_verified=account_verified,
        ai_character_present=video.ai_character_present,
        product_category=video.product_category,
        coding_version=video.coding_version,
        coding_notes=video.coding_notes,
        created_at=video.created_at,
        updated_at=video.updated_at,
        latest_like_count=latest_like,
        latest_comment_count=latest_comment,
        latest_share_count=latest_share,
        latest_view_count=latest_view,
        latest_snapshot_at=latest_at,
    )

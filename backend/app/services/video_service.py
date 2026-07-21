"""
Video service — core CRUD operations with dedup, audit, and author linking.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from app.models.video import Video
from app.models.author import Author
from app.models.metric_snapshot import MetricSnapshot
from app.services.duplicate_detector import find_duplicate_by_platform_id
from app.utils.validators import validate_platform


async def get_or_create_author(
    db: AsyncSession,
    platform: str,
    author_id_hash: str,
    author_data: Optional[Dict[str, Any]] = None,
) -> Author:
    """
    Find an existing author or create a new one.
    """
    stmt = select(Author).where(
        Author.platform == platform,
        Author.author_id_hash == author_id_hash,
    )
    result = await db.execute(stmt)
    author = result.scalar_one_or_none()

    if author:
        # Update public metrics if provided (they change over time)
        if author_data:
            for field in ["author_name_public", "author_profile_url",
                          "follower_count", "following_count",
                          "total_likes_received", "account_verified",
                          "verification_text", "account_bio", "account_type_raw"]:
                if field in author_data and author_data[field] is not None:
                    setattr(author, field, author_data[field])
            author.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(author)
        return author

    author = Author(
        platform=platform,
        author_id_hash=author_id_hash,
        **(author_data or {}),
    )
    db.add(author)
    await db.commit()
    await db.refresh(author)
    return author


async def create_video(
    db: AsyncSession,
    video_data: Dict[str, Any],
    author_data: Optional[Dict[str, Any]] = None,
    author_id_hash: Optional[str] = None,
    created_by: Optional[str] = None,
) -> tuple[Video, bool]:
    """
    Create a video record. Returns (video, is_new).
    Checks for duplicates by (platform, platform_video_id) first.
    If duplicate found, returns existing video with is_new=False.
    """
    platform = video_data.get("platform")
    platform_video_id = video_data.get("platform_video_id")

    if not validate_platform(platform):
        raise ValueError(f"Invalid platform: {platform}")

    # Check for existing video
    existing = await find_duplicate_by_platform_id(db, platform, platform_video_id)
    if existing:
        return existing, False

    # Handle author
    if author_id_hash and author_data:
        author = await get_or_create_author(db, platform, author_id_hash, author_data)
        video_data["author_id"] = author.id

    # Create video
    video = Video(**video_data)
    db.add(video)
    await db.commit()
    await db.refresh(video)

    return video, True


async def get_video_by_id(db: AsyncSession, video_id: str) -> Optional[Video]:
    """Get a video by its UUID."""
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_video_with_author(db: AsyncSession, video_id: str):
    """Get video with author relationship loaded."""
    from sqlalchemy.orm import joinedload
    stmt = (
        select(Video)
        .options(joinedload(Video.author))
        .where(Video.id == video_id)
    )
    result = await db.execute(stmt)
    return result.unique().scalar_one_or_none()


async def list_videos(
    db: AsyncSession,
    platform: Optional[str] = None,
    verification_status: Optional[str] = None,
    collection_method: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_desc: bool = True,
):
    """
    List videos with filtering and pagination.
    """
    stmt = select(Video)

    if platform:
        stmt = stmt.where(Video.platform == platform)
    if verification_status:
        stmt = stmt.where(Video.verification_status == verification_status)
    if collection_method:
        stmt = stmt.where(Video.collection_method == collection_method)
    if keyword:
        stmt = stmt.where(
            or_(
                Video.collection_keyword == keyword,
                Video.video_title.ilike(f"%{keyword}%"),
            )
        )

    # Sort
    sort_col = getattr(Video, sort_by, Video.created_at)
    if sort_desc:
        stmt = stmt.order_by(sort_col.desc())
    else:
        stmt = stmt.order_by(sort_col.asc())

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Paginate
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    videos = result.scalars().all()

    return videos, total


async def update_video_field(
    db: AsyncSession,
    video_id: str,
    field_name: str,
    new_value: Any,
    modified_by: str,
    change_reason: Optional[str] = None,
) -> Optional[Video]:
    """
    Update a single field on a video and record the audit log.
    Returns updated video or None if not found.
    """
    from app.services.audit_service import log_change

    video = await get_video_by_id(db, video_id)
    if not video:
        return None

    old_value = getattr(video, field_name, None)

    # Skip if unchanged
    if str(old_value) == str(new_value):
        return video

    # Update
    setattr(video, field_name, new_value)
    video.updated_at = datetime.utcnow()

    # Audit
    await log_change(
        db=db,
        table_name="videos",
        record_id=video_id,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        modified_by=modified_by,
        change_reason=change_reason,
    )

    await db.commit()
    await db.refresh(video)
    return video


async def bulk_update_video_fields(
    db: AsyncSession,
    video_id: str,
    updates: Dict[str, Any],
    modified_by: str,
    change_reason: Optional[str] = None,
) -> Optional[Video]:
    """Bulk update multiple fields, each with an audit log entry."""
    video = await get_video_with_author(db, video_id)
    if not video:
        return None

    for field_name, new_value in updates.items():
        if not hasattr(video, field_name):
            continue
        old_value = getattr(video, field_name, None)
        if str(old_value) == str(new_value):
            continue
        setattr(video, field_name, new_value)

        from app.services.audit_service import log_change
        await log_change(
            db=db,
            table_name="videos",
            record_id=video_id,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            modified_by=modified_by,
            change_reason=change_reason,
        )

    video.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(video)
    return video


async def create_metric_snapshot(
    db: AsyncSession,
    video_id: str,
    metrics: Dict[str, Any],
    collector_id: Optional[str] = None,
    collection_method: str = "manual",
) -> MetricSnapshot:
    """Create a metric snapshot for a video. Never overwrites."""
    snapshot = MetricSnapshot(
        video_id=video_id,
        like_count=metrics.get("like_count"),
        comment_count=metrics.get("comment_count"),
        share_count=metrics.get("share_count"),
        favorite_count=metrics.get("favorite_count"),
        view_count=metrics.get("view_count"),
        collected_at=datetime.utcnow(),
        metric_visibility=metrics.get("metric_visibility"),
        metric_source=metrics.get("metric_source"),
        collector_id=collector_id,
        collection_method=collection_method,
        notes=metrics.get("notes"),
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def get_video_snapshots(
    db: AsyncSession, video_id: str
) -> List[MetricSnapshot]:
    """Get all metric snapshots for a video, ordered by time."""
    stmt = (
        select(MetricSnapshot)
        .where(MetricSnapshot.video_id == video_id)
        .order_by(MetricSnapshot.collected_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

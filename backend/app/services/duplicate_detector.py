"""
Duplicate detection service.
Based on platform + platform_video_id as primary key.
Similarity detection for manual review (never auto-deletes).
"""
from typing import List, Optional, Set
from difflib import SequenceMatcher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.video import Video


async def find_duplicate_by_platform_id(
    db: AsyncSession, platform: str, platform_video_id: str
) -> Optional[Video]:
    """
    Check if a video already exists by (platform, platform_video_id).
    This is the primary dedup check.
    """
    stmt = select(Video).where(
        Video.platform == platform,
        Video.platform_video_id == platform_video_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_duplicate_by_url(
    db: AsyncSession, url: str
) -> Optional[Video]:
    """
    Check by exact URL match.
    """
    stmt = select(Video).where(
        (Video.video_url == url)
        | (Video.short_url == url)
        | (Video.canonical_url == url)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def compute_title_similarity(title1: str, title2: str) -> float:
    """
    Compute similarity ratio between two video titles.
    Uses SequenceMatcher for string similarity.
    Returns a value between 0 and 1.
    """
    if not title1 or not title2:
        return 0.0
    return SequenceMatcher(None, title1.strip(), title2.strip()).ratio()


async def find_similar_videos(
    db: AsyncSession,
    title: str,
    platform: str,
    threshold: float = 0.85,
    limit: int = 10,
) -> List[Video]:
    """
    Find videos on the same platform with similar titles.
    Returns candidates for manual review — NEVER auto-merge or auto-delete.
    """
    stmt = select(Video).where(
        Video.platform == platform,
        Video.video_title.isnot(None),
    ).limit(200)

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    similar = []
    for video in candidates:
        sim = compute_title_similarity(title, video.video_title or "")
        if sim >= threshold:
            similar.append((video, sim))

    similar.sort(key=lambda x: x[1], reverse=True)
    return [v for v, _ in similar[:limit]]


def assign_duplicate_group(db_videos: List[Video]) -> Optional[str]:
    """
    Given a set of potential duplicate videos, return the group ID to use.
    If any video already has a duplicate_group_id, reuse it.
    Otherwise, generate a new group ID.
    """
    import uuid
    for v in db_videos:
        if v.duplicate_group_id:
            return v.duplicate_group_id
    return str(uuid.uuid4())

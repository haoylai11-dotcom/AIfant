"""
MediaCrawler service — search videos via MediaCrawler API and import them.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.mediacrawler import MediaCrawlerAdapter
from app.services.video_service import create_video, create_metric_snapshot
from app.utils.hashing import hash_author_id
from app.config import settings


def _get_adapter() -> MediaCrawlerAdapter:
    return MediaCrawlerAdapter(
        base_url=settings.MEDIACRAWLER_BASE_URL,
        timeout=settings.MEDIACRAWLER_TIMEOUT,
    )


async def search_and_import_videos(
    db: AsyncSession,
    platform: str,
    keyword: str,
    limit: int = 20,
    sort_type: str = "0",
    publish_time: str = "0",
    search_sort_mode: str = "comprehensive",
) -> Dict[str, Any]:
    """
    Search videos via MediaCrawler and import all results.

    Returns: {imported: int, skipped: int, errors: [...], video_ids: [...]}
    """
    adapter = _get_adapter()
    result = await adapter.search_videos(
        platform=platform,
        keyword=keyword,
        limit=limit,
        sort_type=sort_type,
        publish_time=publish_time,
    )

    imported = 0
    skipped = 0
    errors = []
    video_ids = []

    if not result.success:
        return {
            "imported": 0,
            "skipped": 0,
            "errors": result.errors,
            "video_ids": [],
        }

    search_results = result.video_data.get("_search_results", [])

    for item in search_results:
        try:
            video_data = {
                "platform": item["platform"],
                "platform_video_id": item["platform_video_id"],
                "video_url": item["video_url"] or f"https://www.{platform}.com/.../{item['platform_video_id']}",
                "short_url": item.get("short_url"),
                "video_title": item.get("video_title"),
                "video_description": item.get("video_description"),
                "hashtags": item.get("hashtags"),
                "publish_time": item.get("publish_time"),
                "duration_seconds": item.get("duration_seconds"),
                "cover_url": item.get("cover_url"),
                "collection_method": "licensed_provider",
                "data_source": "mediacrawler",
                "first_collected_at": datetime.utcnow(),
                "public_at_collection": True,
                "collector_version": "0.1.0",
                "collection_keyword": keyword,
                "search_result_rank": search_results.index(item) + 1,
                "search_sort_mode": search_sort_mode,
                "search_date": datetime.utcnow(),
            }

            author_data = {
                "author_name_public": item.get("author_name", ""),
                "follower_count": item.get("follower_count"),
                "account_verified": item.get("account_verified", False),
            }

            author_id_hash = hash_author_id(item.get("author_id_raw", "")) if item.get("author_id_raw") else None

            video, is_new = await create_video(
                db=db,
                video_data=video_data,
                author_data=author_data,
                author_id_hash=author_id_hash,
            )

            if is_new:
                imported += 1
                video_ids.append(video.id)

                # Create initial metric snapshot
                metric_data = {
                    "like_count": item.get("like_count"),
                    "comment_count": item.get("comment_count"),
                    "share_count": item.get("share_count"),
                    "view_count": item.get("view_count"),
                    "metric_source": "mediacrawler_api",
                }
                has_metrics = any(v is not None for v in metric_data.values())
                if has_metrics:
                    await create_metric_snapshot(
                        db=db,
                        video_id=video.id,
                        metrics=metric_data,
                        collection_method="licensed_provider",
                    )
            else:
                skipped += 1

        except Exception as e:
            errors.append({"item": item.get("platform_video_id", "unknown"), "error": str(e)})

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "video_ids": video_ids,
    }


async def get_video_detail_and_import(
    db: AsyncSession,
    platform: str,
    video_id: str,
) -> Dict[str, Any]:
    """Get single video detail via MediaCrawler and import."""
    adapter = _get_adapter()
    result = await adapter.get_video_detail(platform=platform, video_id=video_id)

    if not result.success:
        return {"success": False, "errors": result.errors}

    try:
        vd = result.video_data or {}
        video_data = {
            "platform": platform,
            "platform_video_id": video_id,
            "video_url": vd.get("video_url") or f"https://www.{platform}.com/.../{video_id}",
            "short_url": vd.get("short_url"),
            "video_title": vd.get("video_title"),
            "video_description": vd.get("video_description"),
            "hashtags": vd.get("hashtags"),
            "publish_time": vd.get("publish_time"),
            "duration_seconds": vd.get("duration_seconds"),
            "cover_url": vd.get("cover_url"),
            "collection_method": "licensed_provider",
            "data_source": "mediacrawler",
            "first_collected_at": datetime.utcnow(),
            "public_at_collection": True,
            "collector_version": "0.1.0",
        }

        author_data = result.author_data or {}
        author_id_hash = author_data.get("author_id_hash")
        author_data_only = {k: v for k, v in author_data.items() if k != "author_id_hash"}

        video, is_new = await create_video(
            db=db,
            video_data=video_data,
            author_data=author_data_only,
            author_id_hash=author_id_hash,
        )

        # Metric snapshot
        if result.metric_data:
            await create_metric_snapshot(
                db=db,
                video_id=video.id,
                metrics=result.metric_data,
                collection_method="licensed_provider",
            )

        # Comments
        comments_count = 0
        if result.comments_data:
            from app.models.comment import Comment
            for c in result.comments_data:
                comment = Comment(
                    video_id=video.id,
                    comment_id_hash=c.get("comment_id_hash", ""),
                    comment_text=c.get("comment_text"),
                    comment_time=c.get("comment_time"),
                    like_count=c.get("like_count"),
                    reply_count=c.get("reply_count"),
                    comment_rank=c.get("comment_rank"),
                    sort_mode=c.get("sort_mode", "hot"),
                    parent_comment_id_hash=c.get("parent_comment_id_hash"),
                    commenter_id_hash=c.get("commenter_id_hash"),
                    self_disclosed_age=c.get("self_disclosed_age"),
                    collected_at=datetime.utcnow(),
                )
                db.add(comment)
                comments_count += 1
            await db.commit()

        return {
            "success": True,
            "video_id": video.id,
            "is_new": is_new,
            "comments_imported": comments_count,
        }

    except Exception as e:
        return {"success": False, "errors": [str(e)]}

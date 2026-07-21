"""
Import service — handles CSV/XLSX bulk import and manual link paste.
"""
import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.url_parser import parse_video_url, detect_platform
from app.utils.validators import safe_int, safe_bool, validate_publish_time
from app.utils.hashing import hash_author_id


# CSV column mapping for the standard import template
CSV_COLUMN_MAP = {
    "平台": "platform",
    "platform": "platform",
    "视频ID": "platform_video_id",
    "platform_video_id": "platform_video_id",
    "视频链接": "video_url",
    "video_url": "video_url",
    "短链接": "short_url",
    "short_url": "short_url",
    "标题": "video_title",
    "video_title": "video_title",
    "描述": "video_description",
    "video_description": "video_description",
    "标签": "hashtags",
    "hashtags": "hashtags",
    "发布时间": "publish_time",
    "publish_time": "publish_time",
    "时长秒": "duration_seconds",
    "duration_seconds": "duration_seconds",
    "封面URL": "cover_url",
    "cover_url": "cover_url",
    "作者名": "author_name_public",
    "author_name_public": "author_name_public",
    "作者ID": "author_id_raw",
    "作者粉丝数": "follower_count",
    "follower_count": "follower_count",
    "点赞数": "like_count",
    "like_count": "like_count",
    "评论数": "comment_count",
    "comment_count": "comment_count",
    "分享数": "share_count",
    "share_count": "share_count",
    "收藏数": "favorite_count",
    "favorite_count": "favorite_count",
    "播放数": "view_count",
    "view_count": "view_count",
    "搜索关键词": "collection_keyword",
    "collection_keyword": "collection_keyword",
    "搜索排名": "search_result_rank",
    "search_result_rank": "search_result_rank",
    "搜索排序": "search_sort_mode",
    "search_sort_mode": "search_sort_mode",
    "是否认证": "account_verified",
    "account_verified": "account_verified",
    "认证信息": "verification_text",
    "verification_text": "verification_text",
    "简介": "account_bio",
    "account_bio": "account_bio",
}


# Fields that belong to video (not author, not metrics)
VIDEO_FIELDS = {
    "platform", "platform_video_id", "video_url", "short_url",
    "canonical_url", "video_title", "video_description", "hashtags",
    "publish_time", "duration_seconds", "cover_url",
    "collection_keyword", "search_result_rank", "search_sort_mode",
}

# Fields for author
AUTHOR_FIELDS_CSV = {
    "author_name_public", "author_id_raw", "follower_count",
    "following_count", "total_likes_received", "account_verified",
    "verification_text", "account_bio", "account_type_raw",
}

# Fields for metrics snapshot
METRIC_FIELDS_CSV = {
    "like_count", "comment_count", "share_count",
    "favorite_count", "view_count",
}


class ImportResult:
    """Tracks the result of an import operation."""
    def __init__(self):
        self.total_rows: int = 0
        self.imported: int = 0
        self.skipped_duplicates: int = 0
        self.errors: List[Dict[str, Any]] = []
        self.video_ids: List[str] = []

    @property
    def success_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return self.imported / self.total_rows


def normalize_row(raw_row: Dict[str, str]) -> Dict[str, Any]:
    """
    Normalize CSV row keys to internal field names and parse values.
    """
    normalized = {}
    for key, value in raw_row.items():
        clean_key = key.strip()
        internal_key = CSV_COLUMN_MAP.get(clean_key, clean_key)
        normalized[internal_key] = value.strip() if isinstance(value, str) else value
    return normalized


def parse_row_to_video_data(row: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Parse a normalized row into (video_data, author_data, metric_data) tuples.
    """
    video_data = {}
    author_data = {}
    metric_data = {}

    for key, value in row.items():
        if key in VIDEO_FIELDS:
            video_data[key] = value
        elif key in AUTHOR_FIELDS_CSV:
            author_data[key] = value
        elif key in METRIC_FIELDS_CSV:
            metric_data[key] = value
        else:
            # Unknown field — store in video_data as extra
            video_data[key] = value

    # Type conversions
    if "duration_seconds" in video_data:
        video_data["duration_seconds"] = safe_int(video_data["duration_seconds"])
    if "search_result_rank" in video_data:
        video_data["search_result_rank"] = safe_int(video_data["search_result_rank"])
    if "publish_time" in video_data:
        video_data["publish_time"] = validate_publish_time(video_data["publish_time"])

    # Parse hashtags from comma-separated string to list
    if "hashtags" in video_data and isinstance(video_data["hashtags"], str):
        tags = [t.strip() for t in video_data["hashtags"].split(",") if t.strip()]
        video_data["hashtags"] = tags if tags else None

    # Author conversions
    if "follower_count" in author_data:
        author_data["follower_count"] = safe_int(author_data["follower_count"])
    if "following_count" in author_data:
        author_data["following_count"] = safe_int(author_data["following_count"])
    if "total_likes_received" in author_data:
        author_data["total_likes_received"] = safe_int(author_data["total_likes_received"])
    if "account_verified" in author_data:
        author_data["account_verified"] = safe_bool(author_data["account_verified"])

    # Metric conversions
    for mf in METRIC_FIELDS_CSV:
        if mf in metric_data:
            metric_data[mf] = safe_int(metric_data[mf])

    return video_data, author_data, metric_data


async def import_csv_content(
    db: AsyncSession,
    content: str,
    collection_method: str = "manual_import",
    data_source: str = "manual_import",
    created_by: Optional[str] = None,
) -> ImportResult:
    """
    Import videos from CSV content string.
    """
    from app.services.video_service import create_video, create_metric_snapshot

    result = ImportResult()
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    result.total_rows = len(rows)

    for row in rows:
        try:
            normalized = normalize_row(row)
            video_data, author_data, metric_data = parse_row_to_video_data(normalized)

            # Determine platform from URL if not specified
            if not video_data.get("platform"):
                detected = detect_platform(video_data.get("video_url", ""))
                if detected:
                    video_data["platform"] = detected
                else:
                    result.errors.append({
                        "row": row,
                        "error": "Cannot determine platform",
                    })
                    continue

            # Extract video_id from URL if not provided
            if not video_data.get("platform_video_id"):
                parsed = parse_video_url(video_data.get("video_url", ""))
                if parsed:
                    video_data["platform_video_id"] = parsed.platform_video_id
                else:
                    result.errors.append({
                        "row": row,
                        "error": "Cannot extract video ID from URL",
                    })
                    continue

            # Add collection metadata
            video_data["collection_method"] = collection_method
            video_data["data_source"] = data_source
            video_data["first_collected_at"] = datetime.utcnow()
            video_data["public_at_collection"] = True
            video_data["collector_version"] = "0.1.0"

            if "search_date" not in video_data or video_data["search_date"] is None:
                video_data["search_date"] = datetime.utcnow()

            # Hash author ID if raw ID provided
            author_id_hash = None
            if "author_id_raw" in author_data:
                author_id_hash = hash_author_id(author_data.pop("author_id_raw"))

            # Create video (dedup check is built-in)
            video, is_new = await create_video(
                db=db,
                video_data=video_data,
                author_data=author_data,
                author_id_hash=author_id_hash,
            )

            if is_new:
                result.imported += 1
                result.video_ids.append(video.id)

                # Create initial metric snapshot if metrics provided
                has_metrics = any(metric_data.get(f) is not None for f in METRIC_FIELDS_CSV)
                if has_metrics:
                    metric_data["metric_source"] = collection_method
                    await create_metric_snapshot(
                        db=db,
                        video_id=video.id,
                        metrics=metric_data,
                        collection_method=collection_method,
                        collector_id=created_by,
                    )
            else:
                result.skipped_duplicates += 1

        except Exception as e:
            result.errors.append({"row": row, "error": str(e)})

    return result


async def import_xlsx_content(
    db: AsyncSession,
    content: bytes,
    sheet_name: Optional[str] = None,
    collection_method: str = "manual_import",
    data_source: str = "manual_import",
    created_by: Optional[str] = None,
) -> ImportResult:
    """
    Import videos from XLSX file bytes.
    """
    import pandas as pd

    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name or 0)
        csv_content = df.to_csv(index=False)
        return await import_csv_content(
            db=db,
            content=csv_content,
            collection_method=collection_method,
            data_source=data_source,
            created_by=created_by,
        )
    except Exception as e:
        result = ImportResult()
        result.errors.append({"row": {}, "error": f"XLSX parse error: {str(e)}"})
        return result


async def import_single_link(
    db: AsyncSession,
    url: str,
    metadata: Optional[Dict[str, Any]] = None,
    created_by: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Import a single video from a pasted URL.
    Returns (video_id, error_message).
    """
    from app.services.video_service import create_video

    parsed = parse_video_url(url)
    if not parsed:
        return None, f"Cannot parse URL as Douyin or Kuaishou link: {url}"

    video_data = {
        "platform": parsed.platform,
        "platform_video_id": parsed.platform_video_id,
        "video_url": url,  # Always store the pasted URL
        "short_url": url if parsed.is_short_url else None,
        "collection_method": "manual_import",
        "data_source": "manual_import",
        "first_collected_at": datetime.utcnow(),
        "public_at_collection": True,
        "collector_version": "0.1.0",
    }

    # Merge any additional metadata
    if metadata:
        for key in VIDEO_FIELDS:
            if key in metadata and key not in video_data:
                video_data[key] = metadata[key]
        # Parse publish_time if string
        if "publish_time" in video_data and isinstance(video_data["publish_time"], str):
            video_data["publish_time"] = validate_publish_time(video_data["publish_time"])

    try:
        video, is_new = await create_video(db=db, video_data=video_data)
        if is_new:
            return video.id, None
        else:
            return video.id, "Video already exists in database"
    except Exception as e:
        return None, str(e)

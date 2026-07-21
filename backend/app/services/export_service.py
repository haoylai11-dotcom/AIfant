"""
Export service — generates CSV, XLSX, and JSON exports with configurable fields.
"""
import csv
import io
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.video import Video
from app.models.metric_snapshot import MetricSnapshot
from app.models.comment import Comment
from app.models.author import Author
from app.models.search_session import SearchSession


# Column definitions for export
VIDEO_EXPORT_COLUMNS = [
    # Identity
    ("id", "内部ID"),
    ("platform", "平台"),
    ("platform_video_id", "平台视频ID"),
    ("video_url", "视频链接"),
    ("short_url", "短链接"),
    ("canonical_url", "规范链接"),
    # Content
    ("video_title", "标题"),
    ("video_description", "描述"),
    ("hashtags", "标签"),
    ("publish_time", "发布时间"),
    ("duration_seconds", "时长秒"),
    ("cover_url", "封面URL"),
    # Collection
    ("collection_method", "采集方式"),
    ("data_source", "数据来源"),
    ("verification_status", "复核状态"),
    ("collection_keyword", "采集关键词"),
    ("search_result_rank", "搜索结果排名"),
    ("search_sort_mode", "搜索排序方式"),
    ("search_date", "搜索日期"),
    # Availability
    ("public_at_collection", "采集时公开"),
    ("available_at_followup", "后续可用"),
    ("unavailable_reason", "不可用原因"),
    ("first_collected_at", "首次采集时间"),
    ("last_checked_at", "最后检查时间"),
    ("deleted_or_unavailable_at", "不可用时间"),
    # Research coding
    ("ai_character_present", "AI角色出现"),
    ("apparent_character_age", "角色外表年龄"),
    ("kinship_address_present", "亲属称谓出现"),
    ("kinship_address_text", "亲属称谓文本"),
    ("grandchild_role_enactment", "孙辈角色扮演"),
    ("care_language_present", "关怀语言出现"),
    ("gift_language_present", "礼物语言出现"),
    ("emotional_appeal", "情感诉求"),
    ("rational_appeal", "理性诉求"),
    ("product_category", "产品类别"),
    ("product_name", "产品名称"),
    ("health_claim_present", "健康声称出现"),
    ("purchase_instruction_present", "购买指引出现"),
    ("ai_identity_disclosed", "AI身份披露"),
    ("coding_version", "编码版本"),
    ("coding_notes", "编码备注"),
    # Author (joined)
    ("author_name_public", "作者名称"),
    ("author_profile_url", "作者主页"),
    ("follower_count", "粉丝数"),
    ("account_verified", "是否认证"),
    ("account_bio", "作者简介"),
    ("publisher_type_coded", "发布者类型编码"),
    # Timestamps
    ("created_at", "记录创建时间"),
    ("updated_at", "记录更新时间"),
]


METRIC_EXPORT_COLUMNS = [
    ("id", "快照ID"),
    ("video_id", "视频ID"),
    ("like_count", "点赞数"),
    ("comment_count", "评论数"),
    ("share_count", "分享数"),
    ("favorite_count", "收藏数"),
    ("view_count", "播放数"),
    ("collected_at", "采集时间"),
    ("metric_source", "指标来源"),
    ("collection_method", "采集方式"),
    ("notes", "备注"),
]


COMMENT_EXPORT_COLUMNS = [
    ("id", "评论内部ID"),
    ("comment_id_hash", "评论ID哈希"),
    ("video_id", "视频ID"),
    ("comment_text", "评论文本"),
    ("comment_time", "评论时间"),
    ("like_count", "点赞数"),
    ("reply_count", "回复数"),
    ("comment_rank", "排名"),
    ("sort_mode", "排序方式"),
    ("parent_comment_id_hash", "父评论ID哈希"),
    ("commenter_id_hash", "评论者ID哈希"),
    ("self_disclosed_age", "自述年龄"),
    ("coding_status", "编码状态"),
    ("collected_at", "采集时间"),
    ("created_at", "记录创建时间"),
]


def flatten_hashtags(hashtags: Any) -> str:
    """Convert hashtags list/dict to comma-separated string."""
    if hashtags is None:
        return ""
    if isinstance(hashtags, list):
        return ", ".join(str(t) for t in hashtags)
    if isinstance(hashtags, dict):
        return ", ".join(str(v) for v in hashtags.values())
    return str(hashtags)


def build_video_row(video: Video, columns: List[tuple] = None) -> Dict[str, Any]:
    """
    Build a flat dict row from a Video object.
    Joins author fields when available.
    """
    cols = columns or VIDEO_EXPORT_COLUMNS
    row = {}
    for field, _label in cols:
        if field == "hashtags":
            row[field] = flatten_hashtags(getattr(video, "hashtags", None))
        elif field == "author_name_public":
            row[field] = video.author.author_name_public if video.author else None
        elif field == "author_profile_url":
            row[field] = video.author.author_profile_url if video.author else None
        elif field == "follower_count":
            row[field] = video.author.follower_count if video.author else None
        elif field == "account_verified":
            row[field] = video.author.account_verified if video.author else None
        elif field == "account_bio":
            row[field] = video.author.account_bio if video.author else None
        elif field == "publisher_type_coded":
            row[field] = video.author.publisher_type_coded if video.author else None
        else:
            val = getattr(video, field, None)
            if isinstance(val, datetime):
                val = val.isoformat()
            row[field] = val
    return row


async def export_videos_csv(
    db: AsyncSession,
    video_ids: Optional[List[str]] = None,
    platform: Optional[str] = None,
) -> str:
    """Export videos to CSV string."""
    stmt = select(Video).options(joinedload(Video.author))

    if video_ids:
        stmt = stmt.where(Video.id.in_(video_ids))
    if platform:
        stmt = stmt.where(Video.platform == platform)

    stmt = stmt.order_by(Video.created_at.desc())
    result = await db.execute(stmt)
    videos = result.unique().scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([label for _, label in VIDEO_EXPORT_COLUMNS])

    # Rows
    for video in videos:
        row = build_video_row(video)
        writer.writerow([
            row.get(field, "") for field, _ in VIDEO_EXPORT_COLUMNS
        ])

    return output.getvalue()


async def export_videos_json(
    db: AsyncSession,
    video_ids: Optional[List[str]] = None,
    platform: Optional[str] = None,
) -> str:
    """Export videos to JSON string (with nested author)."""
    from sqlalchemy.orm import joinedload

    stmt = select(Video).options(joinedload(Video.author))

    if video_ids:
        stmt = stmt.where(Video.id.in_(video_ids))
    if platform:
        stmt = stmt.where(Video.platform == platform)

    stmt = stmt.order_by(Video.created_at.desc())
    result = await db.execute(stmt)
    videos = result.unique().scalars().all()

    data = []
    for video in videos:
        row = build_video_row(video)
        # Convert datetime and other non-serializable types
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
        data.append(row)

    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


async def export_videos_xlsx(
    db: AsyncSession,
    video_ids: Optional[List[str]] = None,
    platform: Optional[str] = None,
) -> bytes:
    """Export videos to XLSX bytes."""
    import pandas as pd
    from sqlalchemy.orm import joinedload

    stmt = select(Video).options(joinedload(Video.author))

    if video_ids:
        stmt = stmt.where(Video.id.in_(video_ids))
    if platform:
        stmt = stmt.where(Video.platform == platform)

    stmt = stmt.order_by(Video.created_at.desc())
    result = await db.execute(stmt)
    videos = result.unique().scalars().all()

    rows = [build_video_row(v) for v in videos]
    df = pd.DataFrame(rows)

    # Reorder and rename columns
    col_order = [f for f, _ in VIDEO_EXPORT_COLUMNS if f in df.columns]
    col_names = {f: l for f, l in VIDEO_EXPORT_COLUMNS if f in df.columns}
    df = df[col_order].rename(columns=col_names)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="视频数据", index=False)
    output.seek(0)
    return output.getvalue()


async def export_quality_report(
    db: AsyncSession,
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a data quality report with missing field statistics.
    """
    from sqlalchemy import func

    stmt = select(Video)
    if platform:
        stmt = stmt.where(Video.platform == platform)

    result = await db.execute(stmt)
    videos = result.scalars().all()

    total = len(videos)

    # Per-field completeness
    coding_fields = [
        "ai_character_present", "apparent_character_age",
        "kinship_address_present", "kinship_address_text",
        "grandchild_role_enactment", "care_language_present",
        "gift_language_present", "emotional_appeal", "rational_appeal",
        "product_category", "product_name", "health_claim_present",
        "purchase_instruction_present", "ai_identity_disclosed",
    ]

    metadata_fields = [
        "video_title", "video_description", "hashtags", "publish_time",
        "duration_seconds", "cover_url",
    ]

    engagement_fields = [
        "like_count", "comment_count", "share_count",
        "favorite_count", "view_count",
    ]

    def count_non_null(field: str) -> int:
        return sum(1 for v in videos if getattr(v, field, None) is not None)

    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_videos": total,
        "platform": platform or "all",
        "by_platform": {
            "douyin": sum(1 for v in videos if v.platform == "douyin"),
            "kuaishou": sum(1 for v in videos if v.platform == "kuaishou"),
        },
        "by_verification_status": {},
        "field_completeness": {},
        "latest_snapshot_count": 0,
    }

    # Verification status counts
    for status in ["unverified", "verified", "needs_review", "flagged"]:
        count = sum(1 for v in videos if v.verification_status == status)
        report["by_verification_status"][status] = count

    # Metadata field completeness
    for field in metadata_fields:
        non_null = count_non_null(field)
        report["field_completeness"][f"metadata.{field}"] = {
            "present": non_null,
            "missing": total - non_null,
            "rate": round(non_null / total, 4) if total > 0 else 0.0,
        }

    # Coding field completeness
    for field in coding_fields:
        non_null = count_non_null(field)
        report["field_completeness"][f"coding.{field}"] = {
            "present": non_null,
            "missing": total - non_null,
            "rate": round(non_null / total, 4) if total > 0 else 0.0,
        }

    # Snapshot count (latest)
    snapshot_stmt = select(func.count()).select_from(MetricSnapshot)
    snapshot_result = await db.execute(snapshot_stmt)
    report["latest_snapshot_count"] = snapshot_result.scalar()

    return report

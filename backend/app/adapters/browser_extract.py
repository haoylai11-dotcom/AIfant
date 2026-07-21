"""
Browser extract adapter — handles JSON data extracted from researcher's browser.
The researcher opens a public video page, copies visible fields, and pastes JSON.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.adapters.base import VideoAdapter, AdapterResult
from app.utils.url_parser import parse_video_url, detect_platform
from app.utils.validators import (
    safe_int, safe_bool, validate_publish_time, validate_platform,
    validate_metric_visibility,
)
from app.utils.hashing import hash_author_id, hash_comment_id, hash_commenter_id


class BrowserExtractAdapter(VideoAdapter):
    """
    Adapter for researcher's browser page extraction.

    The researcher opens a video page in their normal browser, the tool
    provides a JavaScript snippet (or the researcher manually copies),
    and the resulting JSON is pasted into this adapter.

    CRITICAL COMPLIANCE: This adapter ONLY extracts publicly visible
    information from the page the researcher is already authorized to view.
    It does NOT bypass any access control, login, or anti-bot measures.
    """

    name = "browser_extract"
    collection_method = "researcher_browser"

    # Fields we expect from browser extraction JSON
    EXPECTED_VIDEO_FIELDS = {
        "url", "title", "description", "hashtags", "publish_time",
        "duration", "cover_url", "author_name", "author_id",
        "author_url", "follower_count", "following_count",
        "total_likes", "verified", "verification_text", "bio",
        "like_count", "comment_count", "share_count",
        "favorite_count", "view_count",
    }

    async def extract(self, input_data: Any) -> AdapterResult:
        """
        Extract from a JSON dict representing browser-extracted page data.

        Expected JSON structure:
        {
            "url": "https://www.douyin.com/video/7123456789...",
            "title": "...",
            "description": "...",
            "hashtags": ["...", "..."],
            "publish_time": "2024-01-15",
            "duration": 60,
            "cover_url": "https://...",
            "author_name": "...",
            "author_id": "raw_platform_id",
            "author_url": "https://...",
            "follower_count": 12345,
            "following_count": 100,
            "total_likes": 50000,
            "verified": true,
            "verification_text": "企业认证",
            "bio": "...",
            "like_count": 1000,
            "comment_count": 50,
            "share_count": 200,
            "favorite_count": 500,
            "view_count": 10000,
            "comments": [
                {
                    "id": "platform_comment_id",
                    "text": "...",
                    "time": "2024-01-15",
                    "likes": 10,
                    "replies": 2,
                    "rank": 1,
                    "commenter_id": "raw_user_id",
                    "parent_id": null,
                    "self_disclosed_age": null
                }
            ],
            "metric_visibility": {...},
            "search_keyword": "...",
            "search_rank": 3,
            "sort_mode": "comprehensive"
        }
        """
        result = AdapterResult(success=False)

        if not isinstance(input_data, dict):
            result.errors.append(f"Expected dict, got {type(input_data)}")
            return result

        url = input_data.get("url")
        if not url:
            result.errors.append("No 'url' field in browser extract data")
            return result

        parsed = parse_video_url(url)
        platform = parsed.platform if parsed else detect_platform(url)

        if not platform:
            result.errors.append(f"Cannot detect platform from URL: {url}")
            return result

        # Build video data
        video_data = {
            "platform": platform,
            "platform_video_id": parsed.platform_video_id if parsed else self._extract_id_from_url(url, platform),
            "video_url": input_data.get("url"),
            "short_url": input_data.get("short_url"),
            "video_title": input_data.get("title"),
            "video_description": input_data.get("description"),
            "hashtags": self._normalize_hashtags(input_data.get("hashtags")),
            "publish_time": self._parse_time(input_data.get("publish_time")),
            "duration_seconds": safe_int(input_data.get("duration")),
            "cover_url": input_data.get("cover_url"),
            "collection_method": "researcher_browser",
            "data_source": "researcher_browser",
            "public_at_collection": True,
            "first_collected_at": datetime.utcnow(),
            "collector_version": "0.1.0",
            "collection_keyword": input_data.get("search_keyword"),
            "search_result_rank": safe_int(input_data.get("search_rank")),
            "search_sort_mode": input_data.get("sort_mode"),
        }
        result.video_data = video_data

        # Build author data
        author_id = input_data.get("author_id")
        author_data = {
            "author_name_public": input_data.get("author_name"),
            "author_profile_url": input_data.get("author_url"),
            "follower_count": safe_int(input_data.get("follower_count")),
            "following_count": safe_int(input_data.get("following_count")),
            "total_likes_received": safe_int(input_data.get("total_likes")),
            "account_verified": safe_bool(input_data.get("verified")),
            "verification_text": input_data.get("verification_text"),
            "account_bio": input_data.get("bio"),
            # We track the raw ID hash, but NOT the raw ID itself
            "author_id_hash": hash_author_id(author_id) if author_id else None,
        }
        result.author_data = author_data

        # Build metric data
        metric_data = {
            "like_count": safe_int(input_data.get("like_count")),
            "comment_count": safe_int(input_data.get("comment_count")),
            "share_count": safe_int(input_data.get("share_count")),
            "favorite_count": safe_int(input_data.get("favorite_count")),
            "view_count": safe_int(input_data.get("view_count")),
            "metric_visibility": input_data.get("metric_visibility"),
            "metric_source": "browser_extract",
        }
        result.metric_data = metric_data

        # Build comments data (if extracted)
        raw_comments = input_data.get("comments", [])
        if raw_comments:
            comments_data = []
            for c in raw_comments:
                comments_data.append({
                    "comment_id_hash": hash_comment_id(str(c.get("id", ""))),
                    "comment_text": c.get("text"),
                    "comment_time": self._parse_time(c.get("time")),
                    "like_count": safe_int(c.get("likes")),
                    "reply_count": safe_int(c.get("replies")),
                    "comment_rank": safe_int(c.get("rank")),
                    "sort_mode": input_data.get("sort_mode"),
                    "parent_comment_id_hash": (
                        hash_comment_id(str(c["parent_id"]))
                        if c.get("parent_id") else None
                    ),
                    "commenter_id_hash": (
                        hash_commenter_id(str(c["commenter_id"]))
                        if c.get("commenter_id") else None
                    ),
                    "self_disclosed_age": c.get("self_disclosed_age"),
                })
            result.comments_data = comments_data

        result.success = True
        return result

    @staticmethod
    def _normalize_hashtags(raw) -> Optional[List[str]]:
        """Normalize hashtags from various input formats."""
        if raw is None:
            return None
        if isinstance(raw, list):
            return [str(t).strip().lstrip("#") for t in raw if str(t).strip()]
        if isinstance(raw, str):
            return [t.strip().lstrip("#") for t in raw.split(",") if t.strip()]
        return None

    @staticmethod
    def _parse_time(time_val) -> Optional[datetime]:
        """Parse time from browser extract."""
        if time_val is None:
            return None
        if isinstance(time_val, datetime):
            return time_val
        return validate_publish_time(str(time_val))

    @staticmethod
    def _extract_id_from_url(url: str, platform: str) -> Optional[str]:
        """Fallback: try to extract ID from URL."""
        import re
        if platform == "douyin":
            m = re.search(r"douyin\.com/video/(\d+)", url)
            if m:
                return m.group(1)
        elif platform == "kuaishou":
            parts = url.rstrip("/").split("/")
            for part in reversed(parts):
                if part and len(part) > 5:
                    return part
        return None

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            **super().get_capabilities(),
            "supports_comments": True,
            "supports_metrics": True,
            "supports_author_details": True,
            "requires_auth": False,
            "compliance_notes": (
                "Extracts only publicly visible page content. "
                "Researcher must be viewing the page in their own browser. "
                "No automated page access, no cookie injection, no API bypass."
            ),
        }


# Browser-side JavaScript snippet for researchers (documentation only, NOT auto-executed)
BROWSER_EXTRACT_SCRIPT = """
// === 抖音/快手视频页面字段提取脚本 ===
// 使用方式：在浏览器DevTools Console中粘贴并运行
// 注意：仅在您正常打开的公开视频页面运行

(function() {
    const result = {};

    // 1. 基础信息
    result.url = window.location.href;
    result.title = document.title;

    // 2. 平台判断
    if (window.location.hostname.includes('douyin.com')) {
        result.platform = 'douyin';
    } else if (window.location.hostname.includes('kuaishou.com')) {
        result.platform = 'kuaishou';
    }

    // 3. 复制结果
    console.log('=== 提取结果（请复制以下JSON） ===');
    console.log(JSON.stringify(result, null, 2));
    console.log('=== 请将以上JSON粘贴到数据管理工具的"浏览器字段提取"页面 ===');

    // 4. 下载为JSON文件
    const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'video_extract_' + Date.now() + '.json';
    a.click();

    return result;
})();
"""

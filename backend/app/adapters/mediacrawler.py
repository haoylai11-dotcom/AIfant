"""
MediaCrawler adapter — integrates MediaCrawler's HTTP API as a data source.

Architecture:
  MediaCrawler runs as a separate service (default http://localhost:8001)
  This adapter calls its API endpoints to:
    1. Search videos by keyword
    2. Get detailed video info (title, author, engagement metrics)

The adapter translates MediaCrawler's response format into our internal data model.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from app.adapters.base import VideoAdapter, AdapterResult
from app.utils.url_parser import parse_video_url, detect_platform
from app.utils.validators import safe_int, validate_publish_time
from app.utils.hashing import hash_author_id, hash_comment_id, hash_commenter_id


class MediaCrawlerAdapter(VideoAdapter):
    """
    Adapter for MediaCrawler HTTP API.

    MediaCrawler service must be running separately.
    Configure MEDIACRAWLER_BASE_URL in .env (default: http://localhost:8001).
    """

    name = "mediacrawler"
    collection_method = "licensed_provider"

    def __init__(self, base_url: str = "http://localhost:8001", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Public API ──

    async def search_videos(
        self,
        platform: str,
        keyword: str,
        limit: int = 20,
        sort_type: str = "0",
        publish_time: str = "0",
    ) -> AdapterResult:
        """
        Search videos on a platform by keyword.

        Args:
            platform: "douyin" or "kuaishou"
            keyword: search keyword
            limit: max results
            sort_type: "0"=comprehensive, "1"=latest, "2"=most liked
            publish_time: "0"=all, "1"=within 24h, "7"=within week, "180"=within 6 months
        """
        result = AdapterResult(success=False)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/{platform}/search",
                    json={
                        "keyword": keyword,
                        "limit": limit,
                        "sort_type": sort_type,
                        "publish_time": publish_time,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError:
            result.errors.append(f"Cannot connect to MediaCrawler at {self.base_url}")
            return result
        except httpx.HTTPStatusError as e:
            result.errors.append(f"MediaCrawler HTTP error: {e.response.status_code}")
            return result
        except Exception as e:
            result.errors.append(f"MediaCrawler error: {str(e)}")
            return result

        videos = []
        raw_list = self._extract_video_list(data, platform)

        for item in raw_list:
            video_info = self._parse_search_item(item, platform, keyword)
            videos.append(video_info)

        result.success = True if videos else False
        result.video_data = {"_search_results": videos, "keyword": keyword, "platform": platform}
        return result

    async def get_video_detail(
        self,
        platform: str,
        video_id: str,
    ) -> AdapterResult:
        """
        Get detailed info for a single video.
        """
        result = AdapterResult(success=False)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/{platform}/detail",
                    json={"video_id": video_id},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError:
            result.errors.append(f"Cannot connect to MediaCrawler at {self.base_url}")
            return result
        except httpx.HTTPStatusError as e:
            result.errors.append(f"MediaCrawler HTTP error: {e.response.status_code}")
            return result
        except Exception as e:
            result.errors.append(f"MediaCrawler error: {str(e)}")
            return result

        parsed = self._parse_detail(data, platform)
        if parsed:
            result.video_data = parsed.get("video_data")
            result.author_data = parsed.get("author_data")
            result.metric_data = parsed.get("metric_data")
            result.comments_data = parsed.get("comments_data", [])
            result.success = True

        return result

    # ── Core adapter interface ──

    async def extract(self, input_data: Any) -> AdapterResult:
        """
        Dispatch based on input type:
        - dict with "keyword" → search
        - dict with "video_id" → get detail
        - str URL → parse and get detail
        """
        if isinstance(input_data, dict):
            if "keyword" in input_data:
                return await self.search_videos(
                    platform=input_data.get("platform", "douyin"),
                    keyword=input_data["keyword"],
                    limit=input_data.get("limit", 20),
                    sort_type=input_data.get("sort_type", "0"),
                    publish_time=input_data.get("publish_time", "0"),
                )
            elif "video_id" in input_data:
                return await self.get_video_detail(
                    platform=input_data.get("platform", "douyin"),
                    video_id=input_data["video_id"],
                )

        if isinstance(input_data, str):
            parsed = parse_video_url(input_data)
            if parsed:
                return await self.get_video_detail(
                    platform=parsed.platform,
                    video_id=parsed.platform_video_id,
                )

        result = AdapterResult(success=False)
        result.errors.append("Invalid input: provide {'keyword': ...} or {'video_id': ...} or URL")
        return result

    # ── Response parsing (handles MediaCrawler's various response formats) ──

    @staticmethod
    def _extract_video_list(data: dict, platform: str) -> list:
        """Extract video list from MediaCrawler response, handling format variations."""
        if not data:
            return []

        # Common paths in MediaCrawler responses
        for key in ["data", "videos", "aweme_list", "results", "feeds"]:
            items = data.get(key)
            if isinstance(items, list) and items:
                return items

        # Some responses have {code: 0, data: {list: [...]}}
        inner = data.get("data", {})
        if isinstance(inner, dict):
            for key in ["list", "videos", "aweme_list", "results"]:
                items = inner.get(key)
                if isinstance(items, list):
                    return items

        return []

    @staticmethod
    def _parse_search_item(item: dict, platform: str, keyword: str) -> Dict[str, Any]:
        """Parse a single search result item into internal video format."""
        # Try to extract video ID from various field names
        video_id = (
            item.get("aweme_id")
            or item.get("video_id")
            or item.get("id")
            or item.get("photo_id")
            or ""
        )

        # Build URL
        if platform == "douyin":
            url = item.get("share_url") or f"https://www.douyin.com/video/{video_id}"
        else:
            url = item.get("share_url") or f"https://www.kuaishou.com/short-video/{video_id}"

        # Author
        author_info = item.get("author", {}) or item.get("author_info", {}) or {}
        author_name = (
            author_info.get("nickname")
            or author_info.get("name")
            or item.get("author_name")
            or item.get("nickname")
        )
        author_id = (
            author_info.get("uid")
            or author_info.get("author_id")
            or author_info.get("user_id")
            or item.get("author_id")
        )

        # Statistics
        stats = item.get("statistics", {}) or item.get("stats", {}) or item
        like_count = safe_int(stats.get("digg_count") or stats.get("like_count") or item.get("like_count"))
        comment_count = safe_int(stats.get("comment_count") or item.get("comment_count"))
        share_count = safe_int(stats.get("share_count") or item.get("share_count"))
        view_count = safe_int(stats.get("play_count") or stats.get("view_count") or item.get("view_count"))

        # Time
        create_time = item.get("create_time") or item.get("publish_time") or item.get("time")
        if isinstance(create_time, (int, float)) and create_time > 1000000000000:
            create_time = datetime.fromtimestamp(create_time / 1000)
        elif isinstance(create_time, (int, float)) and create_time > 1000000000:
            create_time = datetime.fromtimestamp(create_time)
        elif isinstance(create_time, str):
            create_time = validate_publish_time(create_time)
        else:
            create_time = None

        return {
            "platform": platform,
            "platform_video_id": str(video_id) if video_id else "",
            "video_url": url,
            "short_url": item.get("share_url"),
            "video_title": item.get("desc") or item.get("title") or item.get("caption") or "",
            "video_description": item.get("desc") or item.get("description") or "",
            "hashtags": MediaCrawlerAdapter._extract_hashtags(item),
            "publish_time": create_time,
            "duration_seconds": safe_int(item.get("duration") or item.get("video_duration")),
            "cover_url": (
                item.get("cover")
                or item.get("cover_url")
                or (item.get("video", {}) or {}).get("cover", {}).get("url_list", [None])[0]
                or (item.get("video", {}) or {}).get("cover")
            ),
            "author_name": author_name or "",
            "author_id_raw": str(author_id) if author_id else "",
            "follower_count": safe_int(
                (author_info.get("follower_count") or author_info.get("fans_count"))
            ),
            "account_verified": author_info.get("verified", False),
            "like_count": like_count,
            "comment_count": comment_count,
            "share_count": share_count,
            "view_count": view_count,
            "collection_keyword": keyword,
            "search_sort_mode": "comprehensive",
            "collection_method": "licensed_provider",
            "data_source": "mediacrawler",
        }

    @staticmethod
    def _parse_detail(data: dict, platform: str) -> Optional[Dict[str, Any]]:
        """Parse video detail response."""
        items = MediaCrawlerAdapter._extract_video_list(data, platform)
        if not items:
            # Single item response
            items = [data]

        item = items[0]
        parsed = MediaCrawlerAdapter._parse_search_item(item, platform, "")

        # Build author data
        author_info = item.get("author", {}) or item.get("author_info", {}) or {}
        author_data = {
            "author_name_public": parsed.get("author_name", ""),
            "author_id_hash": hash_author_id(str(parsed.get("author_id_raw", ""))),
            "follower_count": parsed.get("follower_count"),
            "account_verified": parsed.get("account_verified", False),
            "verification_text": author_info.get("verification_text", ""),
            "account_bio": author_info.get("bio") or author_info.get("signature", ""),
            "account_type_raw": author_info.get("account_type", ""),
        }

        # Build metric data
        metric_data = {
            "like_count": parsed.get("like_count"),
            "comment_count": parsed.get("comment_count"),
            "share_count": parsed.get("share_count"),
            "view_count": parsed.get("view_count"),
            "metric_source": "mediacrawler_api",
        }

        # Build comments data
        comments_data = []
        raw_comments = item.get("comments") or item.get("comment_list") or []
        for c in raw_comments[:20]:  # Only top 20 comments
            cid = str(c.get("cid") or c.get("comment_id") or "")
            uid = str(c.get("uid") or c.get("user_id") or "")
            comments_data.append({
                "comment_id_hash": hash_comment_id(cid) if cid else "",
                "comment_text": c.get("text") or c.get("content") or "",
                "comment_time": MediaCrawlerAdapter._parse_timestamp(c.get("create_time")),
                "like_count": safe_int(c.get("digg_count") or c.get("like_count")),
                "reply_count": safe_int(c.get("reply_count") or c.get("reply_comment_total")),
                "comment_rank": len(comments_data) + 1,
                "sort_mode": "hot",
                "commenter_id_hash": hash_commenter_id(uid) if uid else "",
                "self_disclosed_age": c.get("self_disclosed_age"),
            })

        return {
            "video_data": parsed,
            "author_data": author_data,
            "metric_data": metric_data,
            "comments_data": comments_data,
        }

    # ── Utilities ──

    @staticmethod
    def _extract_hashtags(item: dict) -> Optional[List[str]]:
        """Extract hashtags from item."""
        # Direct hashtag list
        tags = item.get("hashtags") or item.get("text_extra") or item.get("tag_list")
        if isinstance(tags, list):
            result = []
            for t in tags:
                if isinstance(t, dict):
                    tag = t.get("hashtag_name") or t.get("tag") or t.get("name") or t.get("title") or ""
                else:
                    tag = str(t)
                tag = tag.strip().lstrip("#")
                if tag:
                    result.append(tag)
            return result if result else None

        # Description-based extraction
        desc = item.get("desc") or item.get("title") or ""
        if desc and "#" in desc:
            import re
            found = re.findall(r"#(\S+)", desc)
            return found if found else None

        return None

    @staticmethod
    def _parse_timestamp(ts) -> Optional[datetime]:
        """Parse various timestamp formats."""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            return validate_publish_time(ts)
        if isinstance(ts, (int, float)):
            try:
                if ts > 1000000000000:
                    return datetime.fromtimestamp(ts / 1000)
                elif ts > 1000000000:
                    return datetime.fromtimestamp(ts)
            except (ValueError, OSError):
                pass
        return None

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            **super().get_capabilities(),
            "supports_comments": True,
            "supports_metrics": True,
            "supports_author_details": True,
            "supports_search": True,
            "requires_auth": False,
            "compliance_notes": "Relies on MediaCrawler for data collection. Researcher must ensure MediaCrawler is configured with authorized credentials.",
        }

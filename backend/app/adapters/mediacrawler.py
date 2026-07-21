"""
MediaCrawler adapter — calls MediaCrawler main.py via subprocess.
MediaCrawler is a CLI tool; we invoke it as a subprocess and parse its JSON output.
Requires: MediaCrawler cloned at MEDIACRAWLER_PATH (default: ../MediaCrawler)
"""
import asyncio, json, os, re
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime

from app.adapters.base import VideoAdapter, AdapterResult
from app.utils.validators import safe_int, validate_publish_time
from app.config import settings


class MediaCrawlerAdapter(VideoAdapter):
    name = "mediacrawler"
    collection_method = "licensed_provider"

    def __init__(self):
        path = os.getenv("MEDIACRAWLER_PATH", str(Path(__file__).parent.parent.parent.parent / "MediaCrawler"))
        self.mc_path = Path(path)

    async def search_videos(
        self, platform: str, keyword: str, limit: int = 20,
    ) -> AdapterResult:
        result = AdapterResult(success=False)
        if not self.mc_path.exists():
            result.errors.append(f"MediaCrawler not found at {self.mc_path}. Clone it: git clone https://github.com/NanmiCoder/MediaCrawler")
            return result

        plat = "dy" if platform == "douyin" else "ks"
        cmd = ["python", "main.py", "--platform", plat, "--lt", "qrcode", "--type", "search", "--keywords", keyword]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, cwd=str(self.mc_path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            if proc.returncode != 0:
                err = stderr.decode()[:500] if stderr else "unknown error"
                result.errors.append(f"MediaCrawler exited {proc.returncode}: {err}")
                return result

            # Find output JSON
            data_dir = self.mc_path / "data" / ("douyin" if platform == "douyin" else "kuaishou")
            if not data_dir.exists():
                result.errors.append(f"No data dir: {data_dir}")
                return result

            # MediaCrawler 输出 jsonl 或 json。优先找最新的文件
            json_files = sorted(data_dir.glob("*.json*"), key=os.path.getmtime, reverse=True)
            if not json_files:
                result.errors.append(f"No output found in {data_dir}")
                return result

            raw = []
            found_file = None
            for jf in json_files[:10]:
                try:
                    with open(jf) as f:
                        if jf.suffix == ".jsonl":
                            for line in f:
                                line = line.strip()
                                if line:
                                    raw.append(json.loads(line))
                        else:
                            raw = json.load(f)
                    found_file = jf
                    break
                except: continue

            if not found_file:
                result.errors.append("No readable JSON/JSONL found")
                return result

            items = _extract_list(raw)
            videos = [_parse_item(it, platform, keyword) for it in items[:limit]]
            result.video_data = {"_search_results": videos, "keyword": keyword}
            result.success = bool(videos)
            return result

        except asyncio.TimeoutError:
            result.errors.append("MediaCrawler timed out (120s)")
            return result
        except Exception as e:
            result.errors.append(str(e))
            return result

    async def get_video_detail(self, platform: str, video_id: str) -> AdapterResult:
        return AdapterResult(success=False, errors=["Detail not supported via CLI. Use browser extension."])

    async def extract(self, input_data: Any) -> AdapterResult:
        if isinstance(input_data, dict) and "keyword" in input_data:
            return await self.search_videos(
                platform=input_data.get("platform", "douyin"),
                keyword=input_data["keyword"],
                limit=input_data.get("limit", 20),
            )
        return AdapterResult(success=False, errors=["Provide {'keyword': ...}"])


def _extract_list(data) -> list:
    if isinstance(data, list): return data
    if not isinstance(data, dict): return []
    for k in ("data", "videos", "aweme_list", "results", "content", "list"):
        v = data.get(k)
        if isinstance(v, list): return v
    inner = data.get("data", {})
    if isinstance(inner, dict):
        for k in ("list", "videos", "results", "content"):
            v = inner.get(k)
            if isinstance(v, list): return v
    return []


def _parse_item(item: dict, platform: str, keyword: str) -> dict:
    vid = str(item.get("aweme_id") or item.get("video_id") or item.get("id") or item.get("photo_id") or "")
    url = item.get("share_url") or item.get("video_url") or ""
    if not url:
        url = f"https://www.douyin.com/video/{vid}" if platform == "douyin" else f"https://www.kuaishou.com/short-video/{vid}"

    author = item.get("author", {}) or item.get("author_info", {}) or {}
    author_name = author.get("nickname") or author.get("name") or item.get("author_name") or item.get("nickname") or ""
    author_id = author.get("uid") or author.get("author_id") or item.get("author_id") or ""

    stats = item.get("statistics", {}) or item.get("stats", {}) or item

    ts = item.get("create_time") or item.get("publish_time")
    if isinstance(ts, (int, float)):
        ts = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts)
    elif isinstance(ts, str):
        ts = validate_publish_time(ts)
    else:
        ts = None

    return {
        "platform": platform, "platform_video_id": vid, "video_url": url,
        "short_url": item.get("share_url"), "video_title": item.get("desc") or item.get("title") or item.get("caption") or item.get("video_title") or "",
        "video_description": item.get("desc") or item.get("description") or "",
        "hashtags": _extract_tags(item), "publish_time": ts,
        "duration_seconds": safe_int(item.get("duration")), "cover_url": _extract_cover(item),
        "author_name": author_name, "author_id_raw": str(author_id),
        "follower_count": safe_int(author.get("follower_count") or author.get("fans_count")),
        "account_verified": author.get("verified", False),
        "like_count": safe_int(stats.get("digg_count") or stats.get("like_count")),
        "comment_count": safe_int(stats.get("comment_count")),
        "share_count": safe_int(stats.get("share_count")),
        "view_count": safe_int(stats.get("play_count") or stats.get("view_count")),
    }


def _extract_tags(item: dict) -> Optional[List[str]]:
    tags = item.get("hashtags") or item.get("text_extra") or item.get("tag_list")
    if isinstance(tags, list):
        r = []
        for t in tags:
            tag = (t if isinstance(t, str) else t.get("hashtag_name") or t.get("tag") or t.get("name") or "").lstrip("#")
            if tag: r.append(tag)
        return r or None
    desc = item.get("desc") or ""
    if "#" in desc: return re.findall(r"#(\S+)", desc) or None
    return None


def _extract_cover(item: dict) -> Optional[str]:
    cover = item.get("cover") or item.get("cover_url")
    if isinstance(cover, str) and cover.startswith("http"): return cover
    video = item.get("video") or {}
    if isinstance(video, dict):
        c = video.get("cover")
        if isinstance(c, dict):
            urls = c.get("url_list") or c.get("url")
            if isinstance(urls, list) and urls: return urls[0]
            if isinstance(urls, str): return urls
        if isinstance(c, str): return c
    return None

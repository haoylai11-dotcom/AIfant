"""
URL parser for Douyin and Kuaishou video links.
Extracts platform and video ID from public URLs.
"""
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ParsedVideoUrl:
    platform: str  # "douyin" | "kuaishou"
    platform_video_id: str
    original_url: str
    is_short_url: bool = False


# Douyin URL patterns
DOUYIN_PATTERNS = [
    # Standard: https://www.douyin.com/video/7123456789012345678
    re.compile(r"douyin\.com/video/(\d+)"),
    # Short: https://v.douyin.com/AbCdEfG/
    re.compile(r"v\.douyin\.com/([A-Za-z0-9]+)"),
    # User video: https://www.douyin.com/user/xxx?modal_id=7123456789012345678
    re.compile(r"modal_id=(\d+)"),
]

# Kuaishou URL patterns
KUAISHOU_PATTERNS = [
    # Standard: https://www.kuaishou.com/short-video/abc123def
    re.compile(r"kuaishou\.com/short-video/([A-Za-z0-9]+)"),
    # Short: https://v.kuaishou.com/AbCdEf
    re.compile(r"v\.kuaishou\.com/([A-Za-z0-9]+)"),
    # Photo: https://www.kuaishou.com/photo/abc123
    re.compile(r"kuaishou\.com/photo/([A-Za-z0-9]+)"),
    # Alternative: https://live.kuaishou.com/u/xxx/abc123def
    re.compile(r"kuaishou\.com/u/[^/]+/([A-Za-z0-9]+)"),
    # Short link: https://www.kuaishou.com/f/X-q4jmTBYWEa1pL
    re.compile(r"kuaishou\.com/f/([A-Za-z0-9_-]+)"),
]


def parse_video_url(url: str) -> Optional[ParsedVideoUrl]:
    """
    Parse a video URL and return (platform, video_id).
    Returns None if the URL cannot be parsed as a known platform URL.

    Does NOT access the internet — pure string matching.
    """
    url = url.strip()

    # Try Douyin patterns
    for pattern in DOUYIN_PATTERNS:
        match = pattern.search(url)
        if match:
            video_id = match.group(1)
            is_short = "v.douyin.com" in url
            return ParsedVideoUrl(
                platform="douyin",
                platform_video_id=video_id,
                original_url=url,
                is_short_url=is_short,
            )

    # Try Kuaishou patterns
    for pattern in KUAISHOU_PATTERNS:
        match = pattern.search(url)
        if match:
            video_id = match.group(1)
            is_short = "v.kuaishou.com" in url or "/f/" in url
            return ParsedVideoUrl(
                platform="kuaishou",
                platform_video_id=video_id,
                original_url=url,
                is_short_url=is_short,
            )

    return None


def detect_platform(url: str) -> Optional[str]:
    """Detect platform from URL string without full parse."""
    url_lower = url.lower()
    if "douyin.com" in url_lower or "iesdouyin.com" in url_lower:
        return "douyin"
    if "kuaishou.com" in url_lower:
        return "kuaishou"
    return None

"""
Tests for URL parser utility.
"""
import pytest
from app.utils.url_parser import parse_video_url, detect_platform


class TestParseDouyinUrls:
    def test_standard_url(self):
        result = parse_video_url("https://www.douyin.com/video/7123456789012345678")
        assert result is not None
        assert result.platform == "douyin"
        assert result.platform_video_id == "7123456789012345678"
        assert result.is_short_url is False

    def test_short_url(self):
        result = parse_video_url("https://v.douyin.com/AbCdEfG/")
        assert result is not None
        assert result.platform == "douyin"
        assert result.platform_video_id == "AbCdEfG"
        assert result.is_short_url is True

    def test_modal_id_url(self):
        result = parse_video_url("https://www.douyin.com/user/MS4wLjABAAAAxxx?modal_id=7123456789012345678")
        assert result is not None
        assert result.platform == "douyin"
        assert result.platform_video_id == "7123456789012345678"

    def test_non_video_url(self):
        result = parse_video_url("https://www.douyin.com/discover")
        assert result is None

    def test_empty_url(self):
        result = parse_video_url("")
        assert result is None


class TestParseKuaishouUrls:
    def test_standard_url(self):
        result = parse_video_url("https://www.kuaishou.com/short-video/abc123def")
        assert result is not None
        assert result.platform == "kuaishou"
        assert result.platform_video_id == "abc123def"

    def test_kuaishou_v_short_url(self):
        result = parse_video_url("https://v.kuaishou.com/AbCdEf")
        assert result is not None
        assert result.platform == "kuaishou"
        assert result.platform_video_id == "AbCdEf"
        assert result.is_short_url is True

    def test_photo_url(self):
        result = parse_video_url("https://www.kuaishou.com/photo/xyz789")
        assert result is not None
        assert result.platform == "kuaishou"
        assert result.platform_video_id == "xyz789"

    def test_live_user_url(self):
        result = parse_video_url("https://live.kuaishou.com/u/username/abc123def")
        assert result is not None
        assert result.platform == "kuaishou"
        assert result.platform_video_id == "abc123def"

    def test_non_video_url(self):
        result = parse_video_url("https://www.kuaishou.com/")
        assert result is None


class TestDetectPlatform:
    def test_detect_douyin(self):
        assert detect_platform("https://www.douyin.com/video/123") == "douyin"
        assert detect_platform("https://v.douyin.com/abc") == "douyin"

    def test_detect_kuaishou(self):
        assert detect_platform("https://www.kuaishou.com/short-video/abc") == "kuaishou"
        assert detect_platform("https://v.kuaishou.com/abc") == "kuaishou"

    def test_detect_unknown(self):
        assert detect_platform("https://www.youtube.com/watch?v=abc") is None
        assert detect_platform("") is None


class TestEdgeCases:
    def test_url_with_trailing_slash(self):
        result = parse_video_url("https://www.douyin.com/video/7123456789012345678/")
        assert result.platform_video_id == "7123456789012345678"

    def test_url_with_query_params(self):
        result = parse_video_url("https://www.douyin.com/video/7123456789012345678?from=search")
        assert result.platform_video_id == "7123456789012345678"

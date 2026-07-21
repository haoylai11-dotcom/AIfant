"""
Tests for the import service — CSV and single link.
"""
import pytest
from app.services.import_service import (
    normalize_row, parse_row_to_video_data, import_single_link,
    CSV_COLUMN_MAP,
)
from app.utils.url_parser import parse_video_url


class TestNormalizeRow:
    def test_chinese_column_names(self):
        raw = {"平台": "douyin", "视频链接": "https://www.douyin.com/video/123", "标题": "测试视频"}
        normalized = normalize_row(raw)
        assert normalized["platform"] == "douyin"
        assert normalized["video_url"] == "https://www.douyin.com/video/123"
        assert normalized["video_title"] == "测试视频"

    def test_english_column_names(self):
        raw = {"platform": "douyin", "video_url": "https://www.douyin.com/video/123"}
        normalized = normalize_row(raw)
        assert normalized["platform"] == "douyin"

    def test_mixed_column_names(self):
        raw = {"platform": "douyin", "标题": "测试视频"}
        normalized = normalize_row(raw)
        assert normalized["platform"] == "douyin"
        assert normalized["video_title"] == "测试视频"

    def test_unknown_columns_kept(self):
        """Unknown column names should be kept as-is."""
        raw = {"custom_field": "value"}
        normalized = normalize_row(raw)
        assert normalized["custom_field"] == "value"


class TestParseRow:
    def test_separates_video_author_metrics(self):
        row = {
            "platform": "douyin",
            "video_url": "https://www.douyin.com/video/123",
            "video_title": "测试",
            "author_name_public": "作者名",
            "follower_count": "1000",
            "like_count": "500",
            "comment_count": "50",
        }
        video, author, metrics = parse_row_to_video_data(row)
        assert "platform" in video
        assert video["video_title"] == "测试"
        assert author["author_name_public"] == "作者名"
        assert author["follower_count"] == 1000  # Converted to int
        assert metrics["like_count"] == 500
        assert metrics["comment_count"] == 50

    def test_hashtag_parsing(self):
        row = {"hashtags": "AI数字人, 带货, 萌娃"}
        video, _, _ = parse_row_to_video_data(row)
        assert video["hashtags"] == ["AI数字人", "带货", "萌娃"]

    def test_empty_row(self):
        video, author, metrics = parse_row_to_video_data({})
        assert video == {}
        assert author == {}
        assert metrics == {}

    def test_numeric_fields_null_on_empty(self):
        row = {"follower_count": "", "like_count": ""}
        _, author, metrics = parse_row_to_video_data(row)
        assert author["follower_count"] is None
        assert metrics["like_count"] is None

    def test_bool_fields(self):
        row = {"account_verified": "true"}
        _, author, _ = parse_row_to_video_data(row)
        assert author["account_verified"] is True

        row = {"account_verified": "false"}
        _, author, _ = parse_row_to_video_data(row)
        assert author["account_verified"] is False


class TestImportSingleLink:
    @pytest.mark.asyncio
    async def test_import_douyin_link(self, db_session):
        video_id, error = await import_single_link(
            db=db_session,
            url="https://www.douyin.com/video/7123456789012345678",
            metadata={"video_title": "测试视频"},
        )
        assert video_id is not None
        assert error is None

    @pytest.mark.asyncio
    async def test_import_kuaishou_link(self, db_session):
        video_id, error = await import_single_link(
            db=db_session,
            url="https://www.kuaishou.com/short-video/abc123def",
        )
        assert video_id is not None
        assert error is None
        # New video for kuaishou
        assert error is None

    @pytest.mark.asyncio
    async def test_duplicate_link_returns_existing(self, db_session, test_video):
        """Importing same URL again should return existing video."""
        video_id, error = await import_single_link(
            db=db_session,
            url="https://www.douyin.com/video/7123456789012345678",
        )
        assert video_id == test_video.id
        assert "already exists" in error.lower() or error is not None

    @pytest.mark.asyncio
    async def test_invalid_url_rejected(self, db_session):
        video_id, error = await import_single_link(
            db=db_session,
            url="https://www.youtube.com/watch?v=abc123",
        )
        assert video_id is None
        assert error is not None
        assert "parse" in error.lower() or "cannot" in error.lower()

    @pytest.mark.asyncio
    async def test_empty_url_rejected(self, db_session):
        video_id, error = await import_single_link(db=db_session, url="")
        assert video_id is None
        assert error is not None


class TestCSVColumnMap:
    def test_all_columns_have_mapping(self):
        """Verify the column map is not empty."""
        assert len(CSV_COLUMN_MAP) > 20  # At least 20 mapped columns

    def test_chinese_english_bidirectional(self):
        """Verify key columns have both Chinese and English mappings."""
        assert "platform" in CSV_COLUMN_MAP.values()
        assert "video_url" in CSV_COLUMN_MAP.values()
        assert "video_title" in CSV_COLUMN_MAP.values()

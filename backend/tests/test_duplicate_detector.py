"""
Tests for duplicate detection service.
"""
import pytest
from app.services.duplicate_detector import (
    find_duplicate_by_platform_id,
    find_duplicate_by_url,
    compute_title_similarity,
    assign_duplicate_group,
)


class TestTitleSimilarity:
    def test_identical_titles(self):
        sim = compute_title_similarity("AI数字人带货视频", "AI数字人带货视频")
        assert sim == 1.0

    def test_similar_titles(self):
        sim = compute_title_similarity("AI数字人带货视频", "AI数字人带货")
        assert sim > 0.7

    def test_different_titles(self):
        sim = compute_title_similarity("AI数字人带货视频", "旅游风景记录")
        assert sim < 0.5

    def test_empty_titles(self):
        sim = compute_title_similarity("", "")
        assert sim == 0.0

    def test_none_title(self):
        sim = compute_title_similarity("", None)
        assert sim == 0.0


class TestFindDuplicateByPlatformId:
    @pytest.mark.asyncio
    async def test_no_duplicate(self, db_session):
        video = await find_duplicate_by_platform_id(
            db_session, "douyin", "9999999999999999999"
        )
        assert video is None

    @pytest.mark.asyncio
    async def test_finds_existing(self, db_session, test_video):
        video = await find_duplicate_by_platform_id(
            db_session, "douyin", "7123456789012345678"
        )
        assert video is not None
        assert video.id == test_video.id
        assert video.platform_video_id == "7123456789012345678"

    @pytest.mark.asyncio
    async def test_different_platform_no_duplicate(self, db_session, test_video):
        """Same video ID on different platform should not match."""
        video = await find_duplicate_by_platform_id(
            db_session, "kuaishou", "7123456789012345678"
        )
        assert video is None


class TestFindDuplicateByUrl:
    @pytest.mark.asyncio
    async def test_no_match(self, db_session):
        video = await find_duplicate_by_url(
            db_session, "https://www.douyin.com/video/00000"
        )
        assert video is None

    @pytest.mark.asyncio
    async def test_exact_url_match(self, db_session, test_video):
        video = await find_duplicate_by_url(
            db_session, "https://www.douyin.com/video/7123456789012345678"
        )
        assert video is not None


class TestAssignDuplicateGroup:
    def test_no_existing_group(self):
        """When no videos have a group, a new group ID is generated."""
        class MockVideo:
            duplicate_group_id = None
        group_id = assign_duplicate_group([MockVideo(), MockVideo()])
        assert group_id is not None
        assert len(group_id) == 36  # UUID4 format

    def test_reuses_existing_group(self):
        """When a video already has a group ID, reuse it."""
        class MockVideo:
            def __init__(self, gid):
                self.duplicate_group_id = gid
        existing_id = "existing-group-123"
        group_id = assign_duplicate_group([
            MockVideo(None), MockVideo(existing_id)
        ])
        assert group_id == existing_id

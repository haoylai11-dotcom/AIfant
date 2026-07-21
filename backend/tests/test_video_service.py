"""
Tests for video service — create, read, update with audit.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.services.video_service import (
    create_video, get_video_by_id, get_video_with_author, list_videos,
    update_video_field, bulk_update_video_fields,
)
from app.services.duplicate_detector import find_duplicate_by_platform_id
from app.models.video import Video


class TestCreateVideo:
    @pytest.mark.asyncio
    async def test_create_new_video(self, db_session):
        video_data = {
            "platform": "douyin",
            "platform_video_id": "new_video_001",
            "video_url": "https://www.douyin.com/video/new_video_001",
            "video_title": "新视频",
            "collection_method": "manual_import",
            "data_source": "manual_import",
            "public_at_collection": True,
        }
        video, is_new = await create_video(db=db_session, video_data=video_data)
        assert is_new is True
        assert video.id is not None
        assert video.platform == "douyin"
        assert video.video_title == "新视频"
        assert video.collection_method == "manual_import"

    @pytest.mark.asyncio
    async def test_create_duplicate_returns_existing(self, db_session, test_video):
        """Creating a video with same platform+video_id returns the existing one."""
        video_data = {
            "platform": "douyin",
            "platform_video_id": "7123456789012345678",
            "video_url": "https://www.douyin.com/video/7123456789012345678",
            "video_title": "Should not update",
        }
        video, is_new = await create_video(db=db_session, video_data=video_data)
        assert is_new is False
        assert video.id == test_video.id
        # Title should NOT be overwritten
        assert video.video_title == "AI数字人带货测试视频"

    @pytest.mark.asyncio
    async def test_create_with_invalid_platform(self, db_session):
        video_data = {
            "platform": "youtube",
            "platform_video_id": "abc123",
            "video_url": "https://youtube.com/watch?v=abc123",
        }
        with pytest.raises(ValueError, match="Invalid platform"):
            await create_video(db=db_session, video_data=video_data)

    @pytest.mark.asyncio
    async def test_create_with_author(self, db_session):
        video_data = {
            "platform": "kuaishou",
            "platform_video_id": "ks_video_001",
            "video_url": "https://www.kuaishou.com/short-video/ks001",
            "video_title": "快手测试视频",
            "collection_method": "manual_import",
            "data_source": "manual_import",
            "public_at_collection": True,
        }
        author_data = {
            "author_name_public": "快手测试作者",
            "follower_count": 5000,
        }
        video, is_new = await create_video(
            db=db_session,
            video_data=video_data,
            author_data=author_data,
            author_id_hash="ks_author_hash_001",
        )
        assert is_new is True

        # Refresh with joinedload to resolve relationship
        stmt = select(Video).options(joinedload(Video.author)).where(Video.id == video.id)
        result = await db_session.execute(stmt)
        loaded_video = result.unique().scalar_one()
        assert loaded_video.author is not None
        assert loaded_video.author.author_name_public == "快手测试作者"
        assert loaded_video.author.follower_count == 5000


class TestListVideos:
    @pytest.mark.asyncio
    async def test_list_all(self, db_session, test_video):
        videos, total = await list_videos(db=db_session)
        assert total >= 1

    @pytest.mark.asyncio
    async def test_filter_by_platform(self, db_session, test_video):
        videos, total = await list_videos(db=db_session, platform="douyin")
        assert total >= 1
        assert all(v.platform == "douyin" for v in videos)

        videos, total = await list_videos(db=db_session, platform="kuaishou")
        assert total == 0

    @pytest.mark.asyncio
    async def test_filter_by_verification_status(self, db_session, test_video):
        videos, total = await list_videos(
            db=db_session, verification_status="unverified"
        )
        assert all(v.verification_status == "unverified" for v in videos)

    @pytest.mark.asyncio
    async def test_filter_by_keyword(self, db_session, test_video):
        videos, total = await list_videos(db=db_session, keyword="AI数字人")
        assert total >= 1
        assert any("AI数字人" in (v.video_title or "") for v in videos)

    @pytest.mark.asyncio
    async def test_pagination(self, db_session, test_video):
        videos, total = await list_videos(db=db_session, limit=10, offset=0)
        assert len(videos) <= 10
        assert total >= 1


class TestUpdateVideo:
    @pytest.mark.asyncio
    async def test_update_single_field(self, db_session, test_video):
        video = await update_video_field(
            db=db_session,
            video_id=test_video.id,
            field_name="video_title",
            new_value="更新后的标题",
            modified_by="test_user",
            change_reason="人工复核修正",
        )
        assert video is not None
        assert video.video_title == "更新后的标题"

    @pytest.mark.asyncio
    async def test_update_nonexistent_video(self, db_session):
        video = await update_video_field(
            db=db_session,
            video_id="nonexistent-id",
            field_name="video_title",
            new_value="test",
            modified_by="test",
        )
        assert video is None

    @pytest.mark.asyncio
    async def test_bulk_update(self, db_session, test_video):
        updates = {
            "video_title": "批量更新标题",
            "video_description": "批量更新描述",
            "verification_status": "verified",
        }
        video = await bulk_update_video_fields(
            db=db_session,
            video_id=test_video.id,
            updates=updates,
            modified_by="test_coder",
            change_reason="批量复核",
        )
        assert video.video_title == "批量更新标题"
        assert video.video_description == "批量更新描述"
        assert video.verification_status == "verified"


class TestGetVideo:
    @pytest.mark.asyncio
    async def test_get_existing(self, db_session, test_video):
        video = await get_video_by_id(db_session, test_video.id)
        assert video is not None
        assert video.id == test_video.id

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, db_session):
        video = await get_video_by_id(db_session, "nonexistent")
        assert video is None

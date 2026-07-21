"""
Integration tests — full workflow from import to export.
"""
import pytest
from app.services.import_service import import_single_link
from app.services.video_service import (
    get_video_by_id, create_metric_snapshot, update_video_field,
)
from app.services.export_service import export_videos_csv, export_quality_report


class TestFullWorkflow:
    @pytest.mark.asyncio
    async def test_import_review_snapshot_export(self, db_session, test_user):
        """
        End-to-end workflow:
        1. Import a video via URL
        2. Review and update fields
        3. Create metric snapshots
        4. Export the data
        """
        # Step 1: Import
        video_id, error = await import_single_link(
            db=db_session,
            url="https://www.douyin.com/video/8765432109876543210",
            metadata={
                "video_title": "AI孙女推荐保健品",
                "collection_keyword": "AI孙女",
                "search_result_rank": 1,
                "search_sort_mode": "comprehensive",
            },
        )
        assert video_id is not None
        assert error is None

        # Step 2: Review & update
        video = await update_video_field(
            db=db_session,
            video_id=video_id,
            field_name="verification_status",
            new_value="verified",
            modified_by=test_user.id,
            change_reason="已完成人工复核",
        )
        assert video.verification_status == "verified"

        # Add coding data
        video = await update_video_field(
            db=db_session,
            video_id=video_id,
            field_name="ai_character_present",
            new_value=True,
            modified_by=test_user.id,
            change_reason="编码确认",
        )
        assert video.ai_character_present is True

        # Step 3: Create metric snapshots
        snap1 = await create_metric_snapshot(
            db=db_session,
            video_id=video_id,
            metrics={"like_count": 1200, "comment_count": 80, "view_count": 15000},
            collector_id=test_user.id,
            collection_method="researcher_browser",
        )

        # Second snapshot (e.g., next day)
        snap2 = await create_metric_snapshot(
            db=db_session,
            video_id=video_id,
            metrics={"like_count": 1500, "comment_count": 95},
        )

        assert snap1.like_count == 1200
        assert snap2.like_count == 1500  # Not overwritten!
        assert snap1.view_count == 15000
        assert snap2.view_count is None  # Not collected this time

        # Step 4: Export
        csv_content = await export_videos_csv(db=db_session)
        assert "AI孙女推荐保健品" in csv_content
        assert "douyin" in csv_content

        # Verify quality report
        report = await export_quality_report(db=db_session)
        assert report["total_videos"] >= 1
        assert "field_completeness" in report

    @pytest.mark.asyncio
    async def test_multiple_videos_workflow(self, db_session, test_user):
        """Import multiple videos across platforms."""
        videos_to_import = [
            ("https://www.douyin.com/video/1111111111111111111", "douyin"),
            ("https://www.douyin.com/video/2222222222222222222", "douyin"),
            ("https://www.kuaishou.com/short-video/ksvid001", "kuaishou"),
            ("https://www.kuaishou.com/short-video/ksvid002", "kuaishou"),
        ]

        imported = []
        for url, platform in videos_to_import:
            vid, err = await import_single_link(db=db_session, url=url)
            assert vid is not None
            imported.append(vid)

        # All four should be unique
        assert len(set(imported)) == 4

        # Platform counts from export
        report = await export_quality_report(db=db_session)
        assert report["by_platform"]["douyin"] >= 2
        assert report["by_platform"]["kuaishou"] >= 2

    @pytest.mark.asyncio
    async def test_duplicate_prevention(self, db_session):
        """Verify duplicate prevention works in context of workflow."""
        # First import (must use numeric Douyin video ID)
        vid1, err = await import_single_link(
            db=db_session,
            url="https://www.douyin.com/video/1234567890123456781",
        )
        assert vid1 is not None
        assert err is None

        # Same URL again
        vid2, err2 = await import_single_link(
            db=db_session,
            url="https://www.douyin.com/video/1234567890123456781",
        )
        assert vid2 == vid1  # Same video
        assert err2 is not None  # Has duplicate message

    @pytest.mark.asyncio
    async def test_import_export_roundtrip(self, db_session, test_user):
        """Verify exported CSV can be re-imported."""
        await import_single_link(
            db=db_session,
            url="https://www.douyin.com/video/1234567890123456782",
            metadata={"video_title": "往返测试视频", "collection_keyword": "测试"},
        )

        # Export
        csv_content = await export_videos_csv(db=db_session)

        # Verify key fields are in CSV
        assert "往返测试视频" in csv_content
        assert "1234567890123456782" in csv_content
        assert "douyin" in csv_content

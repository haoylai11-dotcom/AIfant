"""
Tests for snapshot service — ensures old data is never overwritten.
"""
import pytest
from datetime import datetime

from app.models.metric_snapshot import MetricSnapshot
from app.services.video_service import create_metric_snapshot, get_video_snapshots


class TestMetricSnapshots:
    @pytest.mark.asyncio
    async def test_create_snapshot(self, db_session, test_video):
        snapshot = await create_metric_snapshot(
            db=db_session,
            video_id=test_video.id,
            metrics={
                "like_count": 1000,
                "comment_count": 50,
                "share_count": 200,
                "favorite_count": None,
                "view_count": 10000,
            },
            collection_method="manual",
        )
        assert snapshot.id is not None
        assert snapshot.like_count == 1000
        assert snapshot.comment_count == 50
        assert snapshot.favorite_count is None  # Not converted to 0!
        assert snapshot.video_id == test_video.id

    @pytest.mark.asyncio
    async def test_null_metrics_not_converted_to_zero(self, db_session, test_video):
        """Critical test: null (unavailable) metrics must remain null, not 0."""
        snapshot = await create_metric_snapshot(
            db=db_session,
            video_id=test_video.id,
            metrics={
                "like_count": None,
                "comment_count": None,
                "share_count": None,
                "favorite_count": None,
                "view_count": None,
            },
        )
        assert snapshot.like_count is None
        assert snapshot.comment_count is None
        assert snapshot.share_count is None
        assert snapshot.favorite_count is None
        assert snapshot.view_count is None

    @pytest.mark.asyncio
    async def test_multiple_snapshots_dont_overwrite(self, db_session, test_video):
        """Each snapshot should be a new record, not overwrite previous."""
        snap1 = await create_metric_snapshot(
            db=db_session,
            video_id=test_video.id,
            metrics={"like_count": 100, "comment_count": 10},
        )
        snap2 = await create_metric_snapshot(
            db=db_session,
            video_id=test_video.id,
            metrics={"like_count": 200, "comment_count": 20},
        )

        # Both should exist
        snapshots = await get_video_snapshots(db_session, test_video.id)
        assert len(snapshots) == 2

        # First snapshot still has original values
        db_snap1 = [s for s in snapshots if s.id == snap1.id][0]
        assert db_snap1.like_count == 100

        # Second snapshot has new values
        db_snap2 = [s for s in snapshots if s.id == snap2.id][0]
        assert db_snap2.like_count == 200

    @pytest.mark.asyncio
    async def test_snapshots_ordered_by_time(self, db_session, test_video):
        """Snapshots should be returned in chronological order."""
        metrics_groups = [
            {"like_count": 100},
            {"like_count": 200},
            {"like_count": 300},
        ]
        for metrics in metrics_groups:
            await create_metric_snapshot(
                db=db_session,
                video_id=test_video.id,
                metrics=metrics,
            )

        snapshots = await get_video_snapshots(db_session, test_video.id)
        assert len(snapshots) == 3
        # Should be ascending by collected_at
        assert snapshots[0].like_count <= snapshots[1].like_count <= snapshots[2].like_count

    @pytest.mark.asyncio
    async def test_snapshot_with_visibility_tracking(self, db_session, test_video):
        """Test that metric_visibility is properly stored."""
        visibility = {
            "like_count": "visible",
            "comment_count": "visible",
            "share_count": "unavailable_not_displayed",
            "favorite_count": "unavailable_platform_restricted",
            "view_count": "visible",
        }
        snapshot = await create_metric_snapshot(
            db=db_session,
            video_id=test_video.id,
            metrics={
                "like_count": 500,
                "comment_count": 30,
                "share_count": None,
                "favorite_count": None,
                "view_count": 5000,
                "metric_visibility": visibility,
            },
        )
        assert snapshot.metric_visibility == visibility
        assert snapshot.metric_visibility["share_count"] == "unavailable_not_displayed"

    @pytest.mark.asyncio
    async def test_snapshot_with_notes(self, db_session, test_video):
        """Test that notes field is properly stored."""
        snapshot = await create_metric_snapshot(
            db=db_session,
            video_id=test_video.id,
            metrics={"like_count": 50, "notes": "Collected during evening search"},
        )
        assert snapshot.notes == "Collected during evening search"

    @pytest.mark.asyncio
    async def test_snapshot_metadata_fields(self, db_session, test_video):
        """Test collection metadata fields."""
        snapshot = await create_metric_snapshot(
            db=db_session,
            video_id=test_video.id,
            metrics={"like_count": 100},
            collector_id="user_1",
            collection_method="researcher_browser",
        )
        assert snapshot.collector_id == "user_1"
        assert snapshot.collection_method == "researcher_browser"
        assert snapshot.metric_source is None  # Not set by default


class TestSnapshotIsolationEdgeCases:
    @pytest.mark.asyncio
    async def test_snapshots_for_different_videos(self, db_session, test_video, test_author):
        """Snapshots for different videos should not interfere."""
        from app.models.video import Video

        # Create second video
        video2 = Video(
            platform="kuaishou",
            platform_video_id="kuaishou_999",
            video_url="https://www.kuaishou.com/short-video/xyz999",
            video_title="另一个视频",
            collection_method="manual_import",
            data_source="manual_import",
            public_at_collection=True,
            author_id=test_author.id,
        )
        db_session.add(video2)
        await db_session.commit()
        await db_session.refresh(video2)

        # Create snapshots for both
        await create_metric_snapshot(
            db=db_session, video_id=test_video.id,
            metrics={"like_count": 100},
        )
        await create_metric_snapshot(
            db=db_session, video_id=video2.id,
            metrics={"like_count": 999},
        )

        # Verify isolation
        snap1 = await get_video_snapshots(db_session, test_video.id)
        snap2 = await get_video_snapshots(db_session, video2.id)

        assert len(snap1) == 1
        assert len(snap2) == 1
        assert snap1[0].like_count == 100
        assert snap2[0].like_count == 999

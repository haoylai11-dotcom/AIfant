"""
Tests for the audit service.
"""
import pytest
from app.services.audit_service import log_change, get_audit_logs


class TestLogChange:
    @pytest.mark.asyncio
    async def test_log_creates_entry(self, db_session, test_user):
        entry = await log_change(
            db=db_session,
            table_name="videos",
            record_id="test_record_001",
            field_name="video_title",
            old_value="旧标题",
            new_value="新标题",
            modified_by=test_user.id,
            change_reason="人工复核",
        )
        assert entry.id is not None
        assert entry.table_name == "videos"
        assert entry.field_name == "video_title"
        assert entry.old_value == "旧标题"
        assert entry.new_value == "新标题"
        assert entry.modified_by == test_user.id
        assert entry.change_reason == "人工复核"

    @pytest.mark.asyncio
    async def test_log_null_values(self, db_session, test_user):
        """Logging null→value and value→null transitions."""
        # Null → Value
        entry = await log_change(
            db=db_session,
            table_name="videos",
            record_id="test_001",
            field_name="publish_time",
            old_value=None,
            new_value="2024-01-15",
            modified_by=test_user.id,
        )
        assert entry.old_value is None  # SQL NULL stored as None

        # Value → Null
        entry2 = await log_change(
            db=db_session,
            table_name="videos",
            record_id="test_002",
            field_name="publish_time",
            old_value="2024-01-15",
            new_value=None,
            modified_by=test_user.id,
        )
        assert entry2.new_value is None  # SQL NULL stored as None

    @pytest.mark.asyncio
    async def test_log_without_reason(self, db_session, test_user):
        """Change reason is optional."""
        entry = await log_change(
            db=db_session,
            table_name="videos",
            record_id="test_001",
            field_name="duration_seconds",
            old_value="30",
            new_value="60",
            modified_by=test_user.id,
        )
        assert entry.change_reason is None


class TestGetAuditLogs:
    @pytest.mark.asyncio
    async def test_filter_by_table(self, db_session, test_user):
        await log_change(
            db=db_session,
            table_name="videos",
            record_id="r1",
            field_name="title",
            old_value="a",
            new_value="b",
            modified_by=test_user.id,
        )
        await log_change(
            db=db_session,
            table_name="authors",
            record_id="r2",
            field_name="name",
            old_value="x",
            new_value="y",
            modified_by=test_user.id,
        )

        logs = await get_audit_logs(db_session, table_name="videos")
        assert len(logs) >= 1
        assert all(l.table_name == "videos" for l in logs)

    @pytest.mark.asyncio
    async def test_filter_by_record(self, db_session, test_user):
        await log_change(
            db=db_session,
            table_name="videos",
            record_id="specific_record",
            field_name="title",
            old_value="a",
            new_value="b",
            modified_by=test_user.id,
        )

        logs = await get_audit_logs(db_session, record_id="specific_record")
        assert len(logs) >= 1
        assert all(l.record_id == "specific_record" for l in logs)

    @pytest.mark.asyncio
    async def test_empty_when_no_logs(self, db_session):
        logs = await get_audit_logs(db_session, table_name="nonexistent_table")
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_ordered_by_time_desc(self, db_session, test_user):
        """Logs should be returned most recent first."""
        await log_change(
            db=db_session, table_name="videos", record_id="r",
            field_name="f1", old_value="a", new_value="b",
            modified_by=test_user.id, change_reason="first",
        )
        await log_change(
            db=db_session, table_name="videos", record_id="r",
            field_name="f2", old_value="x", new_value="y",
            modified_by=test_user.id, change_reason="second",
        )

        logs = await get_audit_logs(db_session, table_name="videos")
        # Most recent first
        assert logs[0].modified_at >= logs[-1].modified_at

    @pytest.mark.asyncio
    async def test_pagination(self, db_session, test_user):
        for i in range(5):
            await log_change(
                db=db_session, table_name="videos",
                record_id=f"r{i}",
                field_name="f",
                old_value=f"old{i}",
                new_value=f"new{i}",
                modified_by=test_user.id,
            )

        logs = await get_audit_logs(db_session, limit=2, offset=0)
        assert len(logs) == 2

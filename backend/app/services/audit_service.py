"""
Audit service — records all manual changes immutably.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def log_change(
    db: AsyncSession,
    table_name: str,
    record_id: str,
    field_name: str,
    old_value: Optional[str],
    new_value: Optional[str],
    modified_by: str,
    change_reason: Optional[str] = None,
) -> AuditLog:
    """
    Record a change in the audit log.
    Returns the created AuditLog entry.
    """
    entry = AuditLog(
        table_name=table_name,
        record_id=record_id,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        modified_by=modified_by,
        change_reason=change_reason,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_audit_logs(
    db: AsyncSession,
    table_name: Optional[str] = None,
    record_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Retrieve audit logs with optional filters."""
    from sqlalchemy import select
    stmt = select(AuditLog).order_by(AuditLog.modified_at.desc())

    if table_name:
        stmt = stmt.where(AuditLog.table_name == table_name)
    if record_id:
        stmt = stmt.where(AuditLog.record_id == record_id)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

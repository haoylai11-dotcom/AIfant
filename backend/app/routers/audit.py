"""
Audit log router.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.audit_service import get_audit_logs

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def list_audit_logs(
    table_name: Optional[str] = Query(None),
    record_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries with optional filters."""
    logs = await get_audit_logs(
        db=db,
        table_name=table_name,
        record_id=record_id,
        limit=limit,
        offset=offset,
    )
    return {
        "logs": [
            {
                "id": log.id,
                "table_name": log.table_name,
                "record_id": log.record_id,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "modified_by": log.modified_by,
                "modified_at": log.modified_at.isoformat(),
                "change_reason": log.change_reason,
            }
            for log in logs
        ],
        "count": len(logs),
        "limit": limit,
        "offset": offset,
    }

"""
Search session router.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.database import get_db
from app.models.search_session import SearchSession, session_videos
from app.schemas import SearchSessionCreate, SearchSessionResponse

router = APIRouter(prefix="/api/sessions", tags=["search_sessions"])


@router.get("", response_model=List[SearchSessionResponse])
async def list_sessions(
    platform: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all search sessions."""
    stmt = select(SearchSession).order_by(SearchSession.created_at.desc())

    if platform:
        stmt = stmt.where(SearchSession.platform == platform)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return [SearchSessionResponse.model_validate(s) for s in sessions]


@router.post("", response_model=SearchSessionResponse)
async def create_session(
    data: SearchSessionCreate,
    created_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new search session."""
    session = SearchSession(
        session_name=data.session_name,
        platform=data.platform,
        keywords=data.keywords,
        sort_mode=data.sort_mode,
        search_date=data.search_date or datetime.utcnow(),
        notes=data.notes,
        created_by=created_by,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SearchSessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SearchSessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single search session with associated videos."""
    stmt = select(SearchSession).where(SearchSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SearchSessionResponse.model_validate(session)


@router.post("/{session_id}/videos")
async def add_videos_to_session(
    session_id: str,
    video_ids: List[str],
    db: AsyncSession = Depends(get_db),
):
    """Add videos to a search session."""
    stmt = select(SearchSession).where(SearchSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    added = 0
    for idx, vid in enumerate(video_ids):
        stmt = select(session_videos).where(
            session_videos.c.session_id == session_id,
            session_videos.c.video_id == vid,
        )
        exist_result = await db.execute(stmt)
        if exist_result.first():
            continue

        await db.execute(
            session_videos.insert().values(
                session_id=session_id,
                video_id=vid,
                rank_in_session=idx + 1,
            )
        )
        added += 1

    await db.commit()
    return {"added_count": added}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a search session (does not delete associated videos)."""
    stmt = select(SearchSession).where(SearchSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Remove associations first
    await db.execute(
        session_videos.delete().where(session_videos.c.session_id == session_id)
    )
    await db.delete(session)
    await db.commit()
    return {"deleted": True}

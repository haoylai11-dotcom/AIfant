"""
Export router — CSV, XLSX, JSON exports and quality reports.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ExportRequest, QualityReportResponse
from app.services.export_service import (
    export_videos_csv, export_videos_xlsx, export_videos_json,
    export_quality_report,
)

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/videos")
async def export_videos(
    data: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export videos in the specified format."""
    if data.format == "csv":
        content = await export_videos_csv(
            db=db, video_ids=data.video_ids, platform=data.platform,
        )
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=video_export.csv"},
        )
    elif data.format == "xlsx":
        content = await export_videos_xlsx(
            db=db, video_ids=data.video_ids, platform=data.platform,
        )
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=video_export.xlsx"},
        )
    elif data.format == "json":
        content = await export_videos_json(
            db=db, video_ids=data.video_ids, platform=data.platform,
        )
        return Response(
            content=content,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=video_export.json"},
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {data.format}")


@router.get("/quality-report", response_model=QualityReportResponse)
async def get_quality_report(
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get a data quality report with field completeness statistics."""
    report = await export_quality_report(db=db, platform=platform)
    return QualityReportResponse(**report)


@router.get("/methods-appendix")
async def export_methods_appendix(
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a research methods appendix with all collection metadata.
    Includes: search keywords, collection times, field completeness,
    sample screening flow, and available/unavailable counts.
    """
    from app.models.search_session import SearchSession
    from app.models.video import Video
    from sqlalchemy import select, func

    # Get all search sessions
    sessions_stmt = select(SearchSession).order_by(SearchSession.search_date.desc())
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    # Get all keywords used
    all_keywords = set()
    for s in sessions:
        if s.keywords:
            if isinstance(s.keywords, list):
                all_keywords.update(s.keywords)

    # Get video stats
    total_stmt = select(func.count()).select_from(Video)
    total_result = await db.execute(total_stmt)
    total_videos = total_result.scalar()

    douyin_stmt = select(func.count()).where(Video.platform == "douyin")
    douyin_result = await db.execute(douyin_stmt)
    douyin_count = douyin_result.scalar()

    kuaishou_stmt = select(func.count()).where(Video.platform == "kuaishou")
    kuaishou_result = await db.execute(kuaishou_stmt)
    kuaishou_count = kuaishou_result.scalar()

    # Availability stats
    avail_stmt = select(func.count()).where(Video.available_at_followup == False)
    avail_result = await db.execute(avail_stmt)
    unavailable = avail_result.scalar()

    # Collection methods
    methods_stmt = select(
        Video.collection_method, func.count()
    ).group_by(Video.collection_method)
    methods_result = await db.execute(methods_stmt)
    methods = {row[0]: row[1] for row in methods_result.all()}

    report = await export_quality_report(db=db)

    appendix = {
        "generated_at": report["generated_at"],
        "project_name": "抖音-快手AI数字人短视频内容分析",
        "data_collection_summary": {
            "total_videos_collected": total_videos,
            "douyin_videos": douyin_count,
            "kuaishou_videos": kuaishou_count,
            "unavailable_at_followup": unavailable,
        },
        "search_keywords_used": sorted(list(all_keywords)),
        "search_sessions": [
            {
                "name": s.session_name,
                "platform": s.platform,
                "keywords": s.keywords,
                "date": s.search_date.isoformat() if s.search_date else None,
                "sort_mode": s.sort_mode,
            }
            for s in sessions
        ],
        "collection_methods": methods,
        "field_completeness": report["field_completeness"],
        "by_verification_status": report["by_verification_status"],
    }

    return JSONResponse(content=appendix)

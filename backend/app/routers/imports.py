"""
Import router — CSV/XLSX upload and batch import.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ImportResultResponse
from app.services.import_service import import_csv_content, import_xlsx_content

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/csv", response_model=ImportResultResponse)
async def import_csv(
    file: UploadFile = File(...),
    created_by: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload and import a CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be CSV")

    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle BOM

    result = await import_csv_content(
        db=db, content=text, created_by=created_by,
    )
    return ImportResultResponse(
        total_rows=result.total_rows,
        imported=result.imported,
        skipped_duplicates=result.skipped_duplicates,
        errors=result.errors,
        video_ids=result.video_ids,
    )


@router.post("/xlsx", response_model=ImportResultResponse)
async def import_xlsx(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    created_by: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload and import an XLSX file."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="File must be XLSX/XLS")

    content = await file.read()

    result = await import_xlsx_content(
        db=db, content=content, sheet_name=sheet_name, created_by=created_by,
    )
    return ImportResultResponse(
        total_rows=result.total_rows,
        imported=result.imported,
        skipped_duplicates=result.skipped_duplicates,
        errors=result.errors,
        video_ids=result.video_ids,
    )


@router.get("/template/csv")
async def download_csv_template():
    """Download a CSV import template with correct column headers."""
    from fastapi.responses import Response

    headers = [
        "platform", "platform_video_id", "video_url", "short_url",
        "video_title", "video_description", "hashtags",
        "publish_time", "duration_seconds", "cover_url",
        "author_name_public", "author_id_raw",
        "follower_count", "following_count", "total_likes_received",
        "account_verified", "verification_text", "account_bio",
        "account_type_raw",
        "like_count", "comment_count", "share_count",
        "favorite_count", "view_count",
        "collection_keyword", "search_result_rank",
        "search_sort_mode", "search_date",
    ]

    csv_content = ",".join(headers) + "\n"
    # Add template comments as commented lines
    template = (
        "# 抖音/快手视频数据导入模板\n"
        "# 说明：\n"
        "# - platform: douyin 或 kuaishou\n"
        "# - platform_video_id: 从URL中提取的视频数字/字母ID\n"
        "# - 所有互动数据字段留空表示null（未显示），不要填0\n"
        "# - 如某字段在页面上不可见，直接留空\n"
        "# - hashtags: 多个标签用逗号分隔\n"
        "# - 如果URL可以解析出platform和video_id，这两列可不填\n"
        + csv_content
    )

    return Response(
        content=template,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=video_import_template.csv"},
    )

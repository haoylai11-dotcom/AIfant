"""
Coding router — coding assignments, comparison, and inter-rater reliability.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.video import Video
from app.models.coding_record import CodingRecord
from app.schemas import (
    CodingAssignment, CodingComparisonRequest, CodingComparisonResult,
)

router = APIRouter(prefix="/api/coding", tags=["coding"])


@router.get("/tasks/{coder_id}")
async def get_coder_tasks(
    coder_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get videos assigned to a specific coder."""
    stmt = select(Video).where(Video.coder_id == coder_id)

    if status:
        stmt = stmt.where(Video.verification_status == status)

    stmt = stmt.order_by(Video.updated_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    videos = result.scalars().all()

    return {
        "coder_id": coder_id,
        "videos": [
            {
                "id": v.id,
                "platform": v.platform,
                "video_title": v.video_title,
                "ai_character_present": v.ai_character_present,
                "product_category": v.product_category,
                "coding_version": v.coding_version,
                "coding_notes": v.coding_notes,
                "verification_status": v.verification_status,
            }
            for v in videos
        ],
        "total": len(videos),
    }


@router.post("/assign")
async def assign_coding_tasks(
    data: CodingAssignment,
    db: AsyncSession = Depends(get_db),
):
    """Assign video coding tasks to a coder."""
    assigned = 0
    errors = []

    for video_id in data.video_ids:
        stmt = select(Video).where(Video.id == video_id)
        result = await db.execute(stmt)
        video = result.scalar_one_or_none()

        if not video:
            errors.append(f"Video not found: {video_id}")
            continue

        video.coder_id = data.coder_id
        # When a new coder is assigned, allow re-coding
        assigned += 1

    await db.commit()

    return {
        "assigned_count": assigned,
        "errors": errors,
    }


@router.post("/compare", response_model=List[CodingComparisonResult])
async def compare_coders(
    data: CodingComparisonRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Compare coding results between coders and compute reliability.
    Supports Cohen's Kappa and Krippendorff's Alpha.
    """
    import numpy as np

    if len(data.coder_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 coder IDs")

    results = []

    for field in data.fields:
        # Get all coding records for this field by the specified coders
        stmt = (
            select(CodingRecord)
            .where(
                CodingRecord.field_name == field,
                CodingRecord.coder_id.in_(data.coder_ids),
            )
        )
        if data.video_ids:
            stmt = stmt.where(CodingRecord.video_id.in_(data.video_ids))

        result = await db.execute(stmt)
        records = result.scalars().all()

        if len(records) < 2:
            results.append(CodingComparisonResult(
                field=field,
                metric=data.metric,
                value=0.0,
                n_compared=len(records),
                agreement_count=0,
                disagreement_count=0,
            ))
            continue

        # Group records by video_id to compare coder pairs
        by_video = {}
        for r in records:
            if r.video_id not in by_video:
                by_video[r.video_id] = {}
            by_video[r.video_id][r.coder_id] = r.new_value

        # Build comparison pairs
        comparisons = []
        for video_id, coder_values in by_video.items():
            coder_list = list(coder_values.values())
            if len(coder_list) >= 2:
                comparisons.append(coder_list[:2])  # Compare first two coders

        if not comparisons:
            results.append(CodingComparisonResult(
                field=field,
                metric=data.metric,
                value=0.0,
                n_compared=0,
                agreement_count=0,
                disagreement_count=0,
            ))
            continue

        # Calculate agreement
        agreement = sum(1 for a, b in comparisons if a == b)
        disagreement = len(comparisons) - agreement
        raw_agreement = agreement / len(comparisons) if comparisons else 0.0

        # Cohen's Kappa
        if data.metric == "cohens_kappa":
            kappa = _compute_cohens_kappa(comparisons)
            reliability_value = kappa
        elif data.metric == "krippendorff_alpha":
            alpha = _compute_krippendorff_alpha(comparisons)
            reliability_value = alpha
        else:
            reliability_value = raw_agreement

        results.append(CodingComparisonResult(
            field=field,
            metric=data.metric,
            value=round(reliability_value, 4),
            n_compared=len(comparisons),
            agreement_count=agreement,
            disagreement_count=disagreement,
        ))

    return results


def _compute_cohens_kappa(comparisons: List[tuple]) -> float:
    """
    Compute Cohen's Kappa for binary/ nominal data.
    comparisons: list of (coder1_value, coder2_value) tuples.
    """
    n = len(comparisons)
    if n == 0:
        return 0.0

    # Observed agreement
    po = sum(1 for a, b in comparisons if a == b) / n

    # Expected agreement
    all_values = [v for pair in comparisons for v in pair]
    unique = set(all_values)

    pe = 0.0
    for val in unique:
        p1 = sum(1 for a, _ in comparisons if a == val) / n
        p2 = sum(1 for _, b in comparisons if b == val) / n
        pe += p1 * p2

    if pe == 1.0:
        return 1.0

    kappa = (po - pe) / (1 - pe)
    return max(-1.0, min(1.0, kappa))  # Clamp to valid range


def _compute_krippendorff_alpha(comparisons: List[tuple]) -> float:
    """
    Compute Krippendorff's Alpha for nominal data with 2 coders.
    Simplified implementation.
    """
    n = len(comparisons)
    if n == 0:
        return 0.0

    # Convert to numerical codes
    all_values = [v for pair in comparisons for v in pair]
    unique = {v: i for i, v in enumerate(set(all_values))}

    # Build reliability matrix
    num_coders = 2
    matrix = []
    for a, b in comparisons:
        matrix.append([unique[a], unique[b]])

    # Observed disagreement
    do = 0.0
    pair_count = 0
    for i in range(n):
        for j in range(num_coders):
            for k in range(num_coders):
                if j != k:
                    val_j = matrix[i][j]
                    val_k = matrix[i][k]
                    if val_j != val_k:
                        do += 1.0
                    pair_count += 1
    if pair_count == 0:
        return 0.0
    do /= pair_count

    # Expected disagreement
    value_counts = {}
    total_ratings = 0
    for i in range(n):
        for j in range(num_coders):
            v = matrix[i][j]
            value_counts[v] = value_counts.get(v, 0) + 1
            total_ratings += 1

    de = 0.0
    for v1 in unique.values():
        for v2 in unique.values():
            if v1 != v2:
                de += (value_counts.get(v1, 0) / total_ratings) * \
                      (value_counts.get(v2, 0) / (total_ratings - 1))
    if de == 0.0:
        return 0.0

    alpha = 1.0 - (do / de)
    return max(-1.0, min(1.0, alpha))

"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Video schemas ──

class VideoCreate(BaseModel):
    """Schema for creating a video via manual entry."""
    platform: str = Field(..., description="douyin or kuaishou")
    platform_video_id: str
    video_url: str
    short_url: Optional[str] = None
    canonical_url: Optional[str] = None
    video_title: Optional[str] = None
    video_description: Optional[str] = None
    hashtags: Optional[List[str]] = None
    publish_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    cover_url: Optional[str] = None
    collection_keyword: Optional[str] = None
    search_result_rank: Optional[int] = None
    search_sort_mode: Optional[str] = None
    search_date: Optional[datetime] = None
    # Author fields (optional)
    author_name_public: Optional[str] = None
    author_id_raw: Optional[str] = None
    follower_count: Optional[int] = None
    account_verified: Optional[bool] = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in ("douyin", "kuaishou"):
            raise ValueError("platform must be 'douyin' or 'kuaishou'")
        return v


class VideoUpdate(BaseModel):
    """Schema for updating video fields (partial update)."""
    video_title: Optional[str] = None
    video_description: Optional[str] = None
    hashtags: Optional[List[str]] = None
    publish_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    cover_url: Optional[str] = None
    verification_status: Optional[str] = None
    collection_keyword: Optional[str] = None
    search_result_rank: Optional[int] = None
    search_sort_mode: Optional[str] = None
    search_date: Optional[datetime] = None
    available_at_followup: Optional[bool] = None
    unavailable_reason: Optional[str] = None
    duplicate_group_id: Optional[str] = None
    # Coding fields
    ai_character_present: Optional[bool] = None
    apparent_character_age: Optional[str] = None
    kinship_address_present: Optional[bool] = None
    kinship_address_text: Optional[str] = None
    grandchild_role_enactment: Optional[bool] = None
    care_language_present: Optional[bool] = None
    gift_language_present: Optional[bool] = None
    emotional_appeal: Optional[str] = None
    rational_appeal: Optional[str] = None
    product_category: Optional[str] = None
    product_name: Optional[str] = None
    health_claim_present: Optional[bool] = None
    purchase_instruction_present: Optional[bool] = None
    ai_identity_disclosed: Optional[bool] = None
    coding_version: Optional[str] = None
    coding_notes: Optional[str] = None
    change_reason: Optional[str] = None


class VideoResponse(BaseModel):
    """Schema for video API response."""
    id: str
    platform: str
    platform_video_id: str
    video_url: str
    short_url: Optional[str] = None
    video_title: Optional[str] = None
    hashtags: Optional[Any] = None
    publish_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    cover_url: Optional[str] = None
    collection_method: str
    data_source: str
    verification_status: str
    collection_keyword: Optional[str] = None
    search_result_rank: Optional[int] = None
    first_collected_at: Optional[datetime] = None
    public_at_collection: Optional[bool] = None
    available_at_followup: Optional[bool] = None
    unavailable_reason: Optional[str] = None
    author_name: Optional[str] = None
    follower_count: Optional[int] = None
    account_verified: Optional[bool] = None
    # Coding
    ai_character_present: Optional[bool] = None
    product_category: Optional[str] = None
    coding_version: Optional[str] = None
    coding_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    """Schema for paginated video list."""
    videos: List[VideoResponse]
    total: int
    limit: int
    offset: int


# ── Import schemas ──

class SingleLinkImport(BaseModel):
    """Schema for importing a single video link."""
    url: str
    metadata: Optional[Dict[str, Any]] = None


class BrowserExtractImport(BaseModel):
    """Schema for importing browser-extracted JSON data."""
    json_data: Dict[str, Any]


class ImportResultResponse(BaseModel):
    """Schema for import result."""
    total_rows: int
    imported: int
    skipped_duplicates: int
    errors: List[Dict[str, Any]] = []
    video_ids: List[str] = []


# ── Metric snapshot schemas ──

class MetricSnapshotCreate(BaseModel):
    """Schema for creating a metric snapshot."""
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    favorite_count: Optional[int] = None
    view_count: Optional[int] = None
    metric_visibility: Optional[Dict[str, str]] = None
    metric_source: Optional[str] = None
    notes: Optional[str] = None


class MetricSnapshotResponse(BaseModel):
    id: str
    video_id: str
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    favorite_count: Optional[int] = None
    view_count: Optional[int] = None
    collected_at: datetime
    metric_source: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Export schemas ──

class ExportRequest(BaseModel):
    """Schema for export configuration."""
    format: str = Field("csv", description="csv, xlsx, or json")
    video_ids: Optional[List[str]] = None
    platform: Optional[str] = None
    include_coding: bool = True
    include_metrics: bool = False
    include_comments: bool = False

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ("csv", "xlsx", "json"):
            raise ValueError("format must be 'csv', 'xlsx', or 'json'")
        return v


# ── Quality report ──

class QualityReportResponse(BaseModel):
    generated_at: str
    total_videos: int
    platform: str
    by_platform: Dict[str, int]
    by_verification_status: Dict[str, int]
    field_completeness: Dict[str, Dict[str, Any]]
    latest_snapshot_count: int


# ── Search session schemas ──

class SearchSessionCreate(BaseModel):
    session_name: str
    platform: str
    keywords: List[str]
    sort_mode: Optional[str] = "manual"
    search_date: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in ("douyin", "kuaishou", "both"):
            raise ValueError("platform must be 'douyin', 'kuaishou', or 'both'")
        return v


class SearchSessionResponse(BaseModel):
    id: str
    session_name: str
    platform: str
    keywords: Any
    sort_mode: Optional[str] = None
    search_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Comment schemas ──

class CommentImport(BaseModel):
    """Schema for importing a comment."""
    comment_id_raw: str
    comment_text: Optional[str] = None
    comment_time: Optional[datetime] = None
    like_count: Optional[int] = None
    reply_count: Optional[int] = None
    comment_rank: Optional[int] = None
    sort_mode: Optional[str] = None
    parent_comment_id_raw: Optional[str] = None
    commenter_id_raw: Optional[str] = None
    self_disclosed_age: Optional[str] = None


# ── Coding task schemas ──

class CodingAssignment(BaseModel):
    """Schema for assigning coding tasks."""
    video_ids: List[str]
    coder_id: str
    fields: List[str]  # Which coding fields to fill


class CodingComparisonRequest(BaseModel):
    """Schema for computing inter-coder reliability."""
    video_ids: Optional[List[str]] = None
    coder_ids: List[str]
    fields: List[str]
    metric: str = "cohens_kappa"  # or "krippendorff_alpha"


class CodingComparisonResult(BaseModel):
    field: str
    metric: str
    value: float
    n_compared: int
    agreement_count: int
    disagreement_count: int

"""
Video core model — the central entity.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Boolean, Text, Float, DateTime, JSON,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("platform", "platform_video_id", name="uq_platform_video"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Platform identity
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "douyin" | "kuaishou"
    platform_video_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # URLs
    video_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    short_url: Mapped[str] = mapped_column(String(2048), nullable=True)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=True)

    # Content metadata
    video_title: Mapped[str] = mapped_column(String(2000), nullable=True)
    video_description: Mapped[str] = mapped_column(Text, nullable=True)
    hashtags: Mapped[dict] = mapped_column(JSON, nullable=True)  # list of strings
    publish_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    cover_url: Mapped[str] = mapped_column(String(2048), nullable=True)

    # Author
    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("authors.id"), nullable=True, index=True
    )

    # Collection metadata
    collection_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual_import"
    )
    # collection_method values:
    # "official_api", "researcher_browser", "manual_import", "licensed_provider"
    data_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual_import"
    )
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unverified"
    )
    # verification_status: "unverified", "verified", "needs_review", "flagged"

    # Search context
    collection_keyword: Mapped[str] = mapped_column(String(200), nullable=True)
    search_result_rank: Mapped[int] = mapped_column(Integer, nullable=True)
    search_sort_mode: Mapped[str] = mapped_column(String(50), nullable=True)
    search_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Content availability tracking
    public_at_collection: Mapped[bool] = mapped_column(Boolean, default=True)
    available_at_followup: Mapped[bool] = mapped_column(Boolean, nullable=True)
    unavailable_reason: Mapped[str] = mapped_column(String(50), nullable=True)
    # unavailable_reason values:
    # "deleted_by_author", "removed_by_platform",
    # "private_or_permission_changed", "link_invalid",
    # "region_or_login_restricted", "unknown"
    first_collected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    deleted_or_unavailable_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Duplicate management
    duplicate_group_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)

    # Collector metadata
    collector_version: Mapped[str] = mapped_column(String(20), nullable=True)

    # Research coding fields (Phase 1: null, filled by human coders)
    ai_character_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    apparent_character_age: Mapped[str] = mapped_column(String(30), nullable=True)
    kinship_address_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    kinship_address_text: Mapped[str] = mapped_column(Text, nullable=True)
    grandchild_role_enactment: Mapped[bool] = mapped_column(Boolean, nullable=True)
    care_language_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    gift_language_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    emotional_appeal: Mapped[str] = mapped_column(String(50), nullable=True)
    rational_appeal: Mapped[str] = mapped_column(String(50), nullable=True)
    product_category: Mapped[str] = mapped_column(String(100), nullable=True)
    product_name: Mapped[str] = mapped_column(String(500), nullable=True)
    health_claim_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    purchase_instruction_present: Mapped[bool] = mapped_column(Boolean, nullable=True)
    ai_identity_disclosed: Mapped[bool] = mapped_column(Boolean, nullable=True)
    coder_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    coding_version: Mapped[str] = mapped_column(String(20), nullable=True)
    coding_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    author = relationship("Author", back_populates="videos")
    metric_snapshots = relationship(
        "MetricSnapshot", back_populates="video", order_by="MetricSnapshot.collected_at"
    )
    comments = relationship("Comment", back_populates="video")
    media_files = relationship("MediaFile", back_populates="video")
    coding_records = relationship("CodingRecord", back_populates="video")
    search_sessions = relationship(
        "SearchSession",
        secondary="session_videos",
        back_populates="videos",
    )

    def __repr__(self) -> str:
        return f"<Video {self.platform}:{self.platform_video_id}>"

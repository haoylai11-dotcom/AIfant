"""
Metric snapshots — time-series engagement data that never overwrites.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=False, index=True
    )

    # Engagement metrics (all nullable — null = unavailable, not zero)
    like_count: Mapped[int] = mapped_column(Integer, nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=True)
    share_count: Mapped[int] = mapped_column(Integer, nullable=True)
    favorite_count: Mapped[int] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=True)

    # Collection metadata
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    metric_visibility: Mapped[dict] = mapped_column(JSON, nullable=True)
    # Per-field visibility: e.g. {"like_count": "visible", "favorite_count": "unavailable_not_displayed"}
    # Possible values per field:
    # "visible", "unavailable_not_displayed", "unavailable_not_authorized",
    # "unavailable_platform_restricted", "unavailable_parse_failed"
    metric_source: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # e.g. "browser_extract", "official_api", "manual"

    # Snapshot metadata
    collector_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    collection_method: Mapped[str] = mapped_column(String(50), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    video = relationship("Video", back_populates="metric_snapshots")

    def __repr__(self) -> str:
        return f"<MetricSnapshot {self.id} video={self.video_id} at={self.collected_at}>"

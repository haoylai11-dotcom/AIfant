"""
Search session model — organizes videos by collection context.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Text, Table, Column, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# Association table for search sessions <-> videos
session_videos = Table(
    "session_videos",
    Base.metadata,
    Column("session_id", String(36), ForeignKey("search_sessions.id"), primary_key=True),
    Column("video_id", String(36), ForeignKey("videos.id"), primary_key=True),
    Column("rank_in_session", Integer, nullable=True),
)


class SearchSession(Base):
    __tablename__ = "search_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    session_name: Mapped[str] = mapped_column(String(200), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "douyin" | "kuaishou" | "both"
    keywords: Mapped[dict] = mapped_column(JSON, nullable=False)
    # list of keyword strings, e.g. ["AI数字人", "AI萌娃"]

    sort_mode: Mapped[str] = mapped_column(String(50), nullable=True)
    # "comprehensive", "hot", "latest", "manual"
    search_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    collector_version: Mapped[str] = mapped_column(String(20), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    videos = relationship(
        "Video",
        secondary=session_videos,
        back_populates="search_sessions",
    )

    def __repr__(self) -> str:
        return f"<SearchSession {self.session_name} ({self.platform})>"

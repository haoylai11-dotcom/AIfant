"""
Comment model — stored separately from videos.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Identity (hashed)
    comment_id_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # SHA-256 of platform comment ID

    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=False, index=True
    )

    # Content
    comment_text: Mapped[str] = mapped_column(Text, nullable=True)
    comment_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Engagement
    like_count: Mapped[int] = mapped_column(Integer, nullable=True)
    reply_count: Mapped[int] = mapped_column(Integer, nullable=True)

    # Collection context
    comment_rank: Mapped[int] = mapped_column(Integer, nullable=True)
    sort_mode: Mapped[str] = mapped_column(String(30), nullable=True)
    # "hot" | "latest" | "manual"
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Threading
    parent_comment_id_hash: Mapped[str] = mapped_column(
        String(64), nullable=True, index=True
    )

    # Commenter (hashed)
    commenter_id_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    # Only record if the commenter explicitly discloses their age
    self_disclosed_age: Mapped[str] = mapped_column(String(20), nullable=True)

    # Coding status
    coding_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uncoded"
    )
    # "uncoded", "in_progress", "coded", "needs_review"

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    video = relationship("Video", back_populates="comments")

    def __repr__(self) -> str:
        return f"<Comment {self.comment_id_hash[:16]}...>"

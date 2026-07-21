"""
Keyframes — extracted frames at fixed intervals or shot boundaries.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Keyframe(Base):
    __tablename__ = "keyframes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=False, index=True
    )

    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    frame_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Keyframe t={self.timestamp_seconds}s for {self.video_id}>"

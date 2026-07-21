"""
Transcripts — ASR output with timestamps, supporting raw + edited versions.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=False, index=True
    )

    # Transcript content (JSON with segments)
    # Format: [{"start": 0.0, "end": 2.5, "text": "大家好", "confidence": 0.95}, ...]
    content: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Segment-level data
    segments: Mapped[dict] = mapped_column(JSON, nullable=True)
    # Finer-grained: speaker diarization, language segments etc.

    # Processing metadata
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    # e.g. "whisper-large-v3", "aliyun-asr"
    model_version: Mapped[str] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(20), nullable=True)
    is_revised: Mapped[bool] = mapped_column(Boolean, default=False)
    revised_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Transcript for {self.video_id}>"

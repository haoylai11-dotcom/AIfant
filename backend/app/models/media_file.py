"""
Media files — local copies of video/audio/image files for research archives.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=False, index=True
    )

    file_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # "video_original", "audio_extracted", "transcript_raw", "transcript_edited",
    # "keyframe", "ocr_screenshot", "other"
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)  # bytes
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    format: Mapped[str] = mapped_column(String(20), nullable=True)
    # e.g. "mp4", "mp3", "wav", "json", "png"

    transcript_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transcripts.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    video = relationship("Video", back_populates="media_files")

    def __repr__(self) -> str:
        return f"<MediaFile {self.file_type} for {self.video_id}>"

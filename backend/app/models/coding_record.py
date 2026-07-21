"""
Coding records — per-field change history for inter-coder comparison.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CodingRecord(Base):
    __tablename__ = "coding_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    # e.g. "ai_character_present", "kinship_address_present"

    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=True)

    coder_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    coding_version: Mapped[str] = mapped_column(String(20), nullable=True)
    coding_notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    video = relationship("Video", back_populates="coding_records")
    coder = relationship("User", back_populates="coding_records")

    def __repr__(self) -> str:
        return f"<CodingRecord {self.field_name} by {self.coder_id}>"

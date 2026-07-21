"""
Author / publisher model.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, Float, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class PublisherType(str, enum.Enum):
    INDIVIDUAL = "individual_creator"
    MERCHANT = "merchant_or_brand"
    HEALTH_PRO = "health_professional"
    MEDIA = "media_or_institution"
    VIRTUAL = "virtual_influencer_account"
    UNCLEAR = "unclear"


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "douyin" | "kuaishou"
    author_id_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # SHA-256 hash of platform user ID
    author_name_public: Mapped[str] = mapped_column(String(200), nullable=True)
    author_profile_url: Mapped[str] = mapped_column(String(2048), nullable=True)

    # Public account metrics (snapshot at collection time)
    follower_count: Mapped[int] = mapped_column(Integer, nullable=True)
    following_count: Mapped[int] = mapped_column(Integer, nullable=True)
    total_likes_received: Mapped[int] = mapped_column(Integer, nullable=True)

    # Verification
    account_verified: Mapped[bool] = mapped_column(Boolean, nullable=True)
    verification_text: Mapped[str] = mapped_column(String(500), nullable=True)
    account_bio: Mapped[str] = mapped_column(Text, nullable=True)
    account_type_raw: Mapped[str] = mapped_column(String(200), nullable=True)

    # Research coding fields
    publisher_type_coded: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # PublisherType enum values
    publisher_type_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    publisher_type_evidence: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    videos = relationship("Video", back_populates="author")

    def __repr__(self) -> str:
        return f"<Author {self.author_name_public} ({self.platform})>"

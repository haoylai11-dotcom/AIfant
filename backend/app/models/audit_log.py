"""
Audit logs — immutable record of all manual modifications.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    table_name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    record_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)

    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=True)

    modified_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    change_reason: Mapped[str] = mapped_column(String(500), nullable=True)

    # Relationships
    modified_by_user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.table_name}.{self.field_name} by {self.modified_by}>"

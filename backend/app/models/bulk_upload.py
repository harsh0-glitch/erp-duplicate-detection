from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    DateTime,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BulkUploadJob(Base):
    """Tracks asynchronous or batch CSV/Excel bulk upload jobs."""
    __tablename__ = "bulk_upload_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # csv, xlsx
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        server_default=text("'PENDING'"),
        nullable=False,
        index=True,
    )  # PENDING, PROCESSING, COMPLETED, FAILED
    total_rows: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    successful_rows: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    error_summary: Mapped[list] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BulkUploadJob(id={self.id}, filename='{self.filename}', status='{self.status}', total={self.total_rows})>"

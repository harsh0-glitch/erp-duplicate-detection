from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DuplicateDetectionRun(Base):
    """Tracks each duplicate detection execution / request."""
    __tablename__ = "duplicate_detection_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    query_product_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        server_default=text("'PENDING'"),
        nullable=False,
        index=True,
    )  # PENDING, PROCESSING, COMPLETED, FAILED
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_candidates: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)
    execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    run_metadata: Mapped[dict] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    query_product = relationship(
        "Product",
        foreign_keys=[query_product_id],
        back_populates="detection_runs",
    )
    candidates = relationship(
        "DuplicateCandidate",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="DuplicateCandidate.rank",
    )

    def __repr__(self) -> str:
        return f"<DuplicateDetectionRun(id={self.id}, status='{self.status}', candidates={self.total_candidates})>"


class DuplicateCandidate(Base):
    """Stores candidate matches returned by the duplicate detection engine for a run."""
    __tablename__ = "duplicate_candidates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("duplicate_detection_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_product_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    matched_product_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matching_features: Mapped[dict] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    run = relationship("DuplicateDetectionRun", back_populates="candidates")
    query_product = relationship("Product", foreign_keys=[query_product_id])
    matched_product = relationship("Product", foreign_keys=[matched_product_id])
    review = relationship(
        "DuplicateReview",
        back_populates="candidate",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_duplicate_candidates_run_rank", "run_id", "rank"),
        Index("ix_duplicate_candidates_similarity", "similarity_score"),
    )

    def __repr__(self) -> str:
        return f"<DuplicateCandidate(id={self.id}, run_id={self.run_id}, matched_product_id={self.matched_product_id}, score={self.similarity_score})>"


class DuplicateReview(Base):
    """Stores human reviewer decisions for candidate duplicate matches."""
    __tablename__ = "duplicate_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("duplicate_candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    reviewer_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # CONFIRMED or REJECTED
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    candidate = relationship("DuplicateCandidate", back_populates="review")

    def __repr__(self) -> str:
        return f"<DuplicateReview(id={self.id}, candidate_id={self.candidate_id}, decision='{self.decision}')>"

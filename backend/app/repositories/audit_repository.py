import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.audit_log import AuditLog
from app.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class AuditRepository:
    """Data access layer for AuditLog records."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        action: str,
        entity_type: str,
        description: str,
        entity_id: Optional[int] = None,
        user_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Insert and commit a new audit log record."""
        try:
            log_entry = AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                description=description,
                old_values=old_values,
                new_values=new_values,
                log_metadata=metadata,
            )
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            return log_entry
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(f"Failed to create audit log: {exc}")
            # Do not crash calling business operations if audit insertion encounters DB error
            raise DatabaseError("Failed to record audit log.") from exc

    def get_by_id(self, log_id: int) -> Optional[AuditLog]:
        """Fetch a single audit log entry by ID."""
        try:
            return self.db.get(AuditLog, log_id)
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch audit log id={log_id}: {exc}")
            raise DatabaseError("Database error retrieving audit log.") from exc

    def list_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[AuditLog], int]:
        """Query paginated audit logs with optional filters."""
        try:
            stmt = select(AuditLog)

            if action:
                stmt = stmt.where(AuditLog.action == action)
            if entity_type:
                stmt = stmt.where(AuditLog.entity_type == entity_type)
            if entity_id is not None:
                stmt = stmt.where(AuditLog.entity_id == entity_id)
            if user_id:
                stmt = stmt.where(AuditLog.user_id == user_id)
            if start_date:
                stmt = stmt.where(AuditLog.created_at >= start_date)
            if end_date:
                stmt = stmt.where(AuditLog.created_at <= end_date)

            # Count total
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = self.db.execute(count_stmt).scalar_one()

            # Paginate
            offset = (page - 1) * page_size
            stmt = stmt.order_by(AuditLog.id.desc()).offset(offset).limit(page_size)
            items = list(self.db.execute(stmt).scalars().all())

            return items, total
        except SQLAlchemyError as exc:
            logger.error(f"Failed to list audit logs: {exc}")
            raise DatabaseError("Database error listing audit logs.") from exc

    def get_recent_activity(
        self,
        limit: int = 25,
        entity_type: Optional[str] = None,
    ) -> List[AuditLog]:
        """Fetch latest activity records for dashboard streams."""
        try:
            stmt = select(AuditLog)
            if entity_type:
                stmt = stmt.where(AuditLog.entity_type == entity_type)
            stmt = stmt.order_by(AuditLog.id.desc()).limit(limit)
            return list(self.db.execute(stmt).scalars().all())
        except SQLAlchemyError as exc:
            logger.error(f"Failed to fetch recent activity: {exc}")
            raise DatabaseError("Database error retrieving recent activity.") from exc

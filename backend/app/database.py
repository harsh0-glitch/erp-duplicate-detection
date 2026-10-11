from typing import Generator
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy 2.0 Declarative Base
class Base(DeclarativeBase):
    pass


# SQLAlchemy Engine
# pool_pre_ping=True ensures stale/dropped connections to Supabase are automatically recycled
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)

# SessionLocal Factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Check connectivity to Supabase PostgreSQL by executing 'SELECT 1;'."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1;"))
            scalar = result.scalar()
            return scalar == 1
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        return False

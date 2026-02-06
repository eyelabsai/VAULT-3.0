"""
Database configuration. Reads DATABASE_URL from environment.
Use postgresql+asyncpg for async FastAPI; postgresql (psycopg2) for Alembic migrations.
"""

import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


def get_database_url() -> Optional[str]:
    """DATABASE_URL for async driver, e.g. postgresql+asyncpg://user:pass@host:5432/dbname"""
    return os.environ.get("DATABASE_URL")


def get_sync_url() -> Optional[str]:
    """URL with psycopg2 for Alembic: postgresql://... (no +asyncpg)."""
    url = get_database_url()
    if not url:
        return None
    if "+asyncpg" in url:
        return url.replace("postgresql+asyncpg", "postgresql", 1)
    return url


def get_async_engine():
    """Create async engine; returns None if DATABASE_URL is not set."""
    url = get_database_url()
    if not url:
        return None
    return create_async_engine(
        url,
        echo=os.environ.get("SQL_ECHO", "").lower() in ("1", "true", "yes"),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def get_session_factory():
    """Async session factory. Returns None if DATABASE_URL is not set."""
    engine = get_async_engine()
    if engine is None:
        return None
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

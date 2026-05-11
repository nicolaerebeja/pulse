"""Async DB engine + raw-SQL helpers. All app code uses these — never raw SQLAlchemy sessions."""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from pulse.config import settings


class Base(DeclarativeBase):
    """Declarative base used only by pulse.models for Alembic autogeneration."""


engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def fetch_all(sql: str, **params: Any) -> list[dict]:
    """Run SELECT, return all rows as list of dicts."""
    async with _session_factory() as s:
        result = await s.execute(text(sql), params)
        return [dict(row._mapping) for row in result.all()]


async def fetch_one(sql: str, **params: Any) -> dict | None:
    """Run SELECT, return first row as dict or None."""
    async with _session_factory() as s:
        result = await s.execute(text(sql), params)
        row = result.first()
        return dict(row._mapping) if row else None


async def fetch_value(sql: str, **params: Any) -> Any:
    """Run SELECT, return a single scalar value or None."""
    async with _session_factory() as s:
        result = await s.execute(text(sql), params)
        return result.scalar()


async def execute(sql: str, **params: Any) -> int:
    """Run INSERT/UPDATE/DELETE, commit, return affected row count."""
    async with _session_factory() as s:
        result = await s.execute(text(sql), params)
        await s.commit()
        return result.rowcount or 0


@asynccontextmanager
async def transaction() -> AsyncIterator[AsyncSession]:
    """Yield a session in a transaction. Commit on success, rollback on error."""
    async with _session_factory() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise

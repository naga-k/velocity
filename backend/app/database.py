"""SQLite database layer using aiosqlite.

Provides async database access with simple raw SQL — no ORM.
Tables: sessions, messages.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level database path, parsed from settings
_db_path: str = ""


def _resolve_db_path() -> str:
    """Parse the database URL into a file path (or :memory: for tests)."""
    url = settings.database_url
    if url == ":memory:" or url == "sqlite:///:memory:":
        return ":memory:"
    # Strip sqlite:/// prefix
    path = url.removeprefix("sqlite:///")
    return path


async def init_db() -> None:
    """Create tables if they don't exist. Call once at startup."""
    global _db_path
    _db_path = _resolve_db_path()

    # Ensure parent directory exists for file-based DBs
    if _db_path != ":memory:":
        Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(_db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id
            ON messages(session_id)
        """)
        await db.commit()

    logger.info("Database initialized at %s", _db_path)


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager for database connections.

    Usage:
        async with get_db() as db:
            await db.execute("SELECT ...")
    """
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

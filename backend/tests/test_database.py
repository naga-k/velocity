"""Tests for SQLite database layer."""

from __future__ import annotations

import aiosqlite

from app.database import get_db


class TestDatabaseInit:
    async def test_sessions_table_exists(self):
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            )
            row = await cursor.fetchone()
            assert row is not None

    async def test_messages_table_exists(self):
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
            )
            row = await cursor.fetchone()
            assert row is not None

    async def test_messages_index_exists(self):
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND name='idx_messages_session_id'"
            )
            row = await cursor.fetchone()
            assert row is not None

    async def test_sessions_table_schema(self):
        async with get_db() as db:
            cursor = await db.execute("PRAGMA table_info(sessions)")
            columns = {row[1] for row in await cursor.fetchall()}
            assert columns == {"id", "title", "created_at", "updated_at"}

    async def test_messages_table_schema(self):
        async with get_db() as db:
            cursor = await db.execute("PRAGMA table_info(messages)")
            columns = {row[1] for row in await cursor.fetchall()}
            assert columns == {"id", "session_id", "role", "content", "created_at"}


class TestGetDb:
    async def test_connection_returns_rows(self):
        async with get_db() as db:
            await db.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) "
                "VALUES ('test-1', 'Test', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
            )
            await db.commit()

        async with get_db() as db:
            cursor = await db.execute("SELECT id, title FROM sessions")
            row = await cursor.fetchone()
            assert row[0] == "test-1"
            assert row[1] == "Test"

    async def test_foreign_key_cascade(self):
        """Deleting a session should cascade-delete its messages (if PRAGMA enabled)."""
        async with get_db() as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) "
                "VALUES ('s1', 'Test', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
            )
            await db.execute(
                "INSERT INTO messages (id, session_id, role, content, created_at) "
                "VALUES ('m1', 's1', 'user', 'Hello', '2026-01-01T00:00:00')"
            )
            await db.commit()

            await db.execute("DELETE FROM sessions WHERE id = 's1'")
            await db.commit()

            cursor = await db.execute("SELECT COUNT(*) FROM messages WHERE session_id = 's1'")
            count = (await cursor.fetchone())[0]
            assert count == 0

"""Unified session API — the interface Track A and routes consume.

All session/message persistence flows through here.
SQLite for durable storage, Redis for working memory (optional).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.database import get_db
from app.models import SessionMessage, SessionResponse
from app.redis_client import get_session_state, set_session_state  # noqa: F401

# Path to product-context.md (Tier 3 memory)
_PRODUCT_CONTEXT_PATH = Path(__file__).parent.parent / "memory" / "product-context.md"


async def create_session(title: str | None = None) -> SessionResponse:
    """Create a new session and persist it to SQLite."""
    async with get_db() as db:
        # Auto-generate title if not provided
        if not title:
            row = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM sessions")
            count = row[0][0] if row else 0
            title = f"Session {count + 1}"

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        await db.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, title, now.isoformat(), now.isoformat()),
        )
        await db.commit()

    return SessionResponse(id=session_id, title=title, created_at=now, message_count=0)


async def get_session(session_id: str) -> SessionResponse | None:
    """Fetch a session by ID. Returns None if not found."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, title, created_at FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        # Count messages for this session
        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            (session_id,),
        )
        count_row = await count_cursor.fetchone()
        message_count = count_row[0] if count_row else 0

    return SessionResponse(
        id=row[0],
        title=row[1],
        created_at=datetime.fromisoformat(row[2]),
        message_count=message_count,
    )


async def list_sessions() -> list[SessionResponse]:
    """List all sessions, ordered by creation time (newest first)."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT s.id, s.title, s.created_at, COUNT(m.id) as msg_count "
            "FROM sessions s LEFT JOIN messages m ON s.id = m.session_id "
            "GROUP BY s.id ORDER BY s.created_at DESC"
        )
        rows = await cursor.fetchall()

    return [
        SessionResponse(
            id=row[0],
            title=row[1],
            created_at=datetime.fromisoformat(row[2]),
            message_count=row[3],
        )
        for row in rows
    ]


async def delete_session(session_id: str) -> bool:
    """Delete a session and its messages. Returns False if not found."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        )
        if await cursor.fetchone() is None:
            return False

        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()

    return True


async def save_message(session_id: str, role: str, content: str) -> None:
    """Persist a message to SQLite and update session's updated_at."""
    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    async with get_db() as db:
        await db.execute(
            "INSERT INTO messages (id, session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (message_id, session_id, role, content, now.isoformat()),
        )
        await db.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now.isoformat(), session_id),
        )
        await db.commit()


async def get_messages(
    session_id: str, limit: int = 50
) -> list[SessionMessage]:
    """Retrieve recent messages for a session, oldest first."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, session_id, role, content, created_at "
            "FROM messages WHERE session_id = ? "
            "ORDER BY created_at ASC LIMIT ?",
            (session_id, limit),
        )
        rows = await cursor.fetchall()

    return [
        SessionMessage(
            id=row[0],
            session_id=row[1],
            role=row[2],
            content=row[3],
            created_at=datetime.fromisoformat(row[4]),
        )
        for row in rows
    ]


async def get_session_context(session_id: str) -> dict:
    """Build the full context dict that Track A feeds to the Claude Agent SDK.

    Returns:
        {
            "messages": [...],           # Recent messages (dicts)
            "product_context": "...",    # Content of memory/product-context.md
            "session_metadata": {...},   # Title, created_at, message_count
        }
    """
    session = await get_session(session_id)
    messages = await get_messages(session_id)

    # Load Tier 3 product context
    product_context = ""
    if _PRODUCT_CONTEXT_PATH.exists():
        product_context = _PRODUCT_CONTEXT_PATH.read_text(encoding="utf-8")

    return {
        "messages": [msg.model_dump(mode="json") for msg in messages],
        "product_context": product_context,
        "session_metadata": session.model_dump(mode="json") if session else {},
    }

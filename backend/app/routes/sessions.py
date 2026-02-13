"""Session CRUD — in-memory for scaffold. Track C swaps to SQLite/Redis."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models import SessionCreate, SessionResponse

router = APIRouter()

# In-memory session store (replaced by Track C)
_sessions: dict[str, SessionResponse] = {}


@router.post("/api/sessions", response_model=SessionResponse, status_code=201)
async def create_session(body: SessionCreate | None = None) -> SessionResponse:
    session_id = str(uuid.uuid4())
    title = (body.title if body and body.title else f"Session {len(_sessions) + 1}")
    session = SessionResponse(
        id=session_id,
        title=title,
        created_at=datetime.now(timezone.utc),
    )
    _sessions[session_id] = session
    return session


@router.get("/api/sessions", response_model=list[SessionResponse])
async def list_sessions() -> list[SessionResponse]:
    return list(_sessions.values())


@router.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]


@router.delete("/api/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str) -> None:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    del _sessions[session_id]

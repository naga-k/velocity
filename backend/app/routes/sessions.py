"""Session CRUD — backed by SQLite via session_store."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agent import remove_session_client
from app.models import SessionCreate, SessionResponse
from app import session_store

router = APIRouter()


@router.post("/api/sessions", response_model=SessionResponse, status_code=201)
async def create_session(body: SessionCreate | None = None) -> SessionResponse:
    title = body.title if body and body.title else None
    return await session_store.create_session(title)


@router.get("/api/sessions", response_model=list[SessionResponse])
async def list_sessions() -> list[SessionResponse]:
    return await session_store.list_sessions()


@router.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    session = await session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/api/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str) -> None:
    deleted = await session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    await remove_session_client(session_id)

"""Pydantic models — the shared contract between backend and frontend.

These models define the request/response shapes and SSE event data structures.
All tracks must respect these shapes. Changes here require coordinating
with the frontend TypeScript types in frontend/lib/types.ts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """POST /api/chat request body."""
    message: str = Field(min_length=1)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context: dict | None = None  # unused in scaffold


class SessionCreate(BaseModel):
    """POST /api/sessions request body."""
    title: str | None = None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class SessionResponse(BaseModel):
    """Session metadata returned by session CRUD endpoints."""
    id: str
    title: str
    created_at: datetime
    message_count: int = 0


class HealthResponse(BaseModel):
    """GET /api/health response."""
    status: Literal["ok", "degraded"]
    version: str = "0.1.0"
    anthropic_configured: bool


# ---------------------------------------------------------------------------
# SSE event data shapes (what goes in the `data` field of each SSE event)
# ---------------------------------------------------------------------------

class ThinkingEventData(BaseModel):
    """data for event: thinking"""
    text: str


class ErrorEventData(BaseModel):
    """data for event: error"""
    message: str
    recoverable: bool = True


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0


class DoneEventData(BaseModel):
    """data for event: done"""
    tokens_used: TokenUsage = Field(default_factory=TokenUsage)
    agents_used: list[str] = Field(default_factory=list)


# Note: `text` event data is a bare JSON string, not a model.
# e.g. event: text\ndata: "Hello world"


# ---------------------------------------------------------------------------
# Agent activity models (used by Track A, defined here as contract)
# ---------------------------------------------------------------------------

class AgentActivityData(BaseModel):
    """data for event: agent_activity"""
    agent: str
    status: Literal["running", "completed"]
    task: str


class CitationData(BaseModel):
    """data for event: citation"""
    type: Literal["slack", "linear", "web"]
    url: str
    title: str
    snippet: str


class ToolCallData(BaseModel):
    """data for event: tool_call"""
    tool: str
    params: dict


# ---------------------------------------------------------------------------
# Persistence models (Track C — messages table)
# ---------------------------------------------------------------------------

class SessionMessage(BaseModel):
    """A single message in a conversation session."""
    id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

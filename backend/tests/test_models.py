"""Tests for Pydantic models — verify contracts serialize correctly."""

import uuid

from app.models import (
    ChatRequest,
    DoneEventData,
    ErrorEventData,
    HealthResponse,
    SessionCreate,
    SessionResponse,
    ThinkingEventData,
    TokenUsage,
    AgentActivityData,
    CitationData,
    ToolCallData,
)


class TestChatRequest:
    def test_minimal_request(self):
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.session_id  # auto-generated UUID
        assert req.context is None

    def test_auto_generates_session_id(self):
        r1 = ChatRequest(message="a")
        r2 = ChatRequest(message="b")
        assert r1.session_id != r2.session_id
        uuid.UUID(r1.session_id)  # validates it's a real UUID

    def test_explicit_session_id(self):
        req = ChatRequest(message="Hi", session_id="custom-123")
        assert req.session_id == "custom-123"

    def test_with_context(self):
        req = ChatRequest(message="Hi", context={"project": "API"})
        assert req.context == {"project": "API"}

    def test_serialization_roundtrip(self):
        req = ChatRequest(message="Hello", session_id="abc")
        data = req.model_dump()
        assert data["message"] == "Hello"
        assert data["session_id"] == "abc"
        restored = ChatRequest(**data)
        assert restored == req


class TestSessionModels:
    def test_session_create_defaults(self):
        s = SessionCreate()
        assert s.title is None

    def test_session_create_with_title(self):
        s = SessionCreate(title="Sprint Planning")
        assert s.title == "Sprint Planning"

    def test_session_response(self):
        from datetime import datetime
        s = SessionResponse(
            id="abc",
            title="Test",
            created_at=datetime(2026, 2, 13),
            message_count=5,
        )
        data = s.model_dump()
        assert data["id"] == "abc"
        assert data["message_count"] == 5

    def test_session_response_default_count(self):
        from datetime import datetime
        s = SessionResponse(
            id="abc",
            title="Test",
            created_at=datetime(2026, 2, 13),
        )
        assert s.message_count == 0


class TestHealthResponse:
    def test_ok_status(self):
        h = HealthResponse(status="ok", anthropic_configured=True)
        assert h.status == "ok"
        assert h.version == "0.1.0"

    def test_degraded_status(self):
        h = HealthResponse(status="degraded", anthropic_configured=False)
        assert h.status == "degraded"
        assert not h.anthropic_configured


class TestSSEEventModels:
    def test_thinking_event(self):
        e = ThinkingEventData(text="Planning agents...")
        assert e.model_dump() == {"text": "Planning agents..."}

    def test_error_event_defaults(self):
        e = ErrorEventData(message="Rate limit")
        assert e.recoverable is True

    def test_error_event_non_recoverable(self):
        e = ErrorEventData(message="Auth failed", recoverable=False)
        assert not e.recoverable

    def test_done_event_defaults(self):
        e = DoneEventData()
        assert e.tokens_used.input == 0
        assert e.tokens_used.output == 0
        assert e.agents_used == []

    def test_done_event_with_usage(self):
        e = DoneEventData(
            tokens_used=TokenUsage(input=500, output=1000),
            agents_used=["research"],
        )
        data = e.model_dump()
        assert data["tokens_used"]["input"] == 500
        assert data["agents_used"] == ["research"]

    def test_agent_activity(self):
        a = AgentActivityData(agent="research", status="running", task="Search Slack")
        assert a.model_dump()["status"] == "running"

    def test_citation(self):
        c = CitationData(
            type="slack",
            url="https://slack.com/msg/123",
            title="Sprint Discussion",
            snippet="We should prioritize...",
        )
        assert c.type == "slack"

    def test_tool_call(self):
        t = ToolCallData(tool="slack_search", params={"query": "sprint"})
        assert t.params["query"] == "sprint"

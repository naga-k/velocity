"""Tests for chat endpoint — SSE streaming with mocked agent."""

from __future__ import annotations

import json
from unittest.mock import patch

from app.models import ErrorEventData


def parse_sse_events(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of {event, data} dicts."""
    events = []
    current_event = None
    current_data = None

    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data = line[len("data:"):].strip()
        elif line == "" and current_event is not None and current_data is not None:
            events.append({"event": current_event, "data": current_data})
            current_event = None
            current_data = None

    # Handle last event if no trailing newline
    if current_event is not None and current_data is not None:
        events.append({"event": current_event, "data": current_data})

    return events


class TestChatEndpoint:
    async def test_chat_returns_sse_stream(self, client, mock_anthropic):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    async def test_chat_emits_text_and_done(self, client, mock_anthropic):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "text" in event_types
        assert "done" in event_types
        # done should be last
        assert event_types[-1] == "done"

    async def test_chat_text_is_bare_string(self, client, mock_anthropic):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        text_events = [e for e in events if e["event"] == "text"]

        assert len(text_events) > 0
        for e in text_events:
            parsed = json.loads(e["data"])
            # text events should be bare strings
            assert isinstance(parsed, str)

    async def test_chat_text_reconstructs_message(self, client, mock_anthropic):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        text_events = [e for e in events if e["event"] == "text"]

        full_text = "".join(json.loads(e["data"]) for e in text_events)
        assert full_text == "Hello from Claude!"

    async def test_chat_done_has_token_usage(self, client, mock_anthropic):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        done_events = [e for e in events if e["event"] == "done"]

        assert len(done_events) == 1
        done_data = json.loads(done_events[0]["data"])
        assert "tokens_used" in done_data
        assert "input" in done_data["tokens_used"]
        assert "output" in done_data["tokens_used"]

    async def test_chat_auto_generates_session_id(self, client, mock_anthropic):
        """session_id is optional — should not 422."""
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200

    async def test_chat_with_explicit_session_id(self, client, mock_anthropic):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": "my-session"},
        )
        assert resp.status_code == 200

    async def test_chat_rejects_empty_message(self, client, mock_anthropic):
        resp = await client.post(
            "/api/chat",
            json={"message": ""},
        )
        assert resp.status_code == 422

    async def test_chat_error_when_no_api_key(self, client):
        with patch("app.agent.settings") as mock_settings:
            mock_settings.anthropic_configured = False

            resp = await client.post(
                "/api/chat",
                json={"message": "Hello"},
            )

        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "error" in event_types
        error_event = next(e for e in events if e["event"] == "error")
        error_data = json.loads(error_event["data"])
        assert "not configured" in error_data["message"].lower()
        assert error_data["recoverable"] is False

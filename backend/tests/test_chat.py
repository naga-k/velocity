"""Tests for chat endpoint — SSE streaming with mocked Claude Agent SDK."""

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
    async def test_chat_returns_sse_stream(self, client, mock_agent_sdk):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    async def test_chat_emits_text_and_done(self, client, mock_agent_sdk):
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

    async def test_chat_text_is_bare_string(self, client, mock_agent_sdk):
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

    async def test_chat_text_reconstructs_message(self, client, mock_agent_sdk):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        text_events = [e for e in events if e["event"] == "text"]

        full_text = "".join(json.loads(e["data"]) for e in text_events)
        assert full_text == "Hello from Claude!"

    async def test_chat_done_has_token_usage(self, client, mock_agent_sdk):
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

    async def test_chat_auto_generates_session_id(self, client, mock_agent_sdk):
        """session_id is optional — should not 422."""
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        assert resp.status_code == 200

    async def test_chat_with_explicit_session_id(self, client, mock_agent_sdk):
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": "my-session"},
        )
        assert resp.status_code == 200

    async def test_chat_rejects_empty_message(self, client, mock_agent_sdk):
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


class TestThinkingEvents:
    """Test that thinking deltas are emitted as SSE thinking events."""

    async def test_thinking_event_emitted(self, client, mock_agent_sdk):
        from tests.conftest import (
            make_mock_result_message,
            make_mock_stream_text_deltas,
            make_mock_stream_thinking_delta,
        )

        mock_agent_sdk["set_messages"]([
            make_mock_stream_thinking_delta("Analyzing the request..."),
            *make_mock_stream_text_deltas("Here is my answer."),
            make_mock_result_message(),
        ])

        resp = await client.post(
            "/api/chat",
            json={"message": "Prioritize the backlog"},
        )
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "thinking" in event_types
        thinking_event = next(e for e in events if e["event"] == "thinking")
        data = json.loads(thinking_event["data"])
        assert data["text"] == "Analyzing the request..."

    async def test_thinking_then_text(self, client, mock_agent_sdk):
        from tests.conftest import (
            make_mock_result_message,
            make_mock_stream_text_deltas,
            make_mock_stream_thinking_delta,
        )

        mock_agent_sdk["set_messages"]([
            make_mock_stream_thinking_delta("Planning..."),
            *make_mock_stream_text_deltas("The answer is 42."),
            make_mock_result_message(),
        ])

        resp = await client.post(
            "/api/chat",
            json={"message": "What is the answer?"},
        )
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        # thinking should come before text
        thinking_idx = event_types.index("thinking")
        text_idx = event_types.index("text")
        assert thinking_idx < text_idx


class TestAgentActivityEvents:
    """Test that subagent invocations emit agent_activity SSE events."""

    async def test_subagent_emits_agent_activity(self, client, mock_agent_sdk):
        from tests.conftest import (
            make_mock_result_message,
            make_mock_stream_text_deltas,
            make_mock_subagent_message,
        )

        mock_agent_sdk["set_messages"]([
            make_mock_subagent_message(
                agent_type="research",
                description="Searching Slack for feedback",
            ),
            *make_mock_stream_text_deltas("Based on the research, here are the findings."),
            make_mock_result_message(),
        ])

        resp = await client.post(
            "/api/chat",
            json={"message": "What feedback exists?"},
        )
        events = parse_sse_events(resp.text)
        activity_events = [e for e in events if e["event"] == "agent_activity"]

        assert len(activity_events) >= 1
        data = json.loads(activity_events[0]["data"])
        assert data["agent"] == "research"
        assert data["status"] == "running"
        assert "Slack" in data["task"]

    async def test_agents_used_in_done(self, client, mock_agent_sdk):
        from tests.conftest import (
            make_mock_result_message,
            make_mock_stream_text_deltas,
            make_mock_subagent_message,
        )

        mock_agent_sdk["set_messages"]([
            make_mock_subagent_message(agent_type="research"),
            make_mock_subagent_message(agent_type="backlog"),
            *make_mock_stream_text_deltas("Summary of findings."),
            make_mock_result_message(),
        ])

        resp = await client.post(
            "/api/chat",
            json={"message": "Sprint status"},
        )
        events = parse_sse_events(resp.text)
        done_event = next(e for e in events if e["event"] == "done")
        done_data = json.loads(done_event["data"])

        assert "research" in done_data["agents_used"]
        assert "backlog" in done_data["agents_used"]


class TestToolCallEvents:
    """Test that non-Task tool calls emit tool_call SSE events."""

    async def test_tool_call_emitted(self, client, mock_agent_sdk):
        from tests.conftest import (
            make_mock_result_message,
            make_mock_stream_text_deltas,
            make_mock_tool_call_message,
        )

        mock_agent_sdk["set_messages"]([
            make_mock_tool_call_message(
                tool_name="mcp__pm_tools__read_product_context",
                tool_input={},
            ),
            *make_mock_stream_text_deltas("Here is the product context."),
            make_mock_result_message(),
        ])

        resp = await client.post(
            "/api/chat",
            json={"message": "Load context"},
        )
        events = parse_sse_events(resp.text)
        tool_events = [e for e in events if e["event"] == "tool_call"]

        assert len(tool_events) >= 1
        data = json.loads(tool_events[0]["data"])
        assert data["tool"] == "mcp__pm_tools__read_product_context"


class TestGracefulDegradation:
    """Test that the agent works without MCP integrations configured."""

    async def test_works_without_slack_linear(self, client, mock_agent_sdk):
        """With no Slack/Linear tokens, agent should still respond."""
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "text" in event_types
        assert "done" in event_types
        assert "error" not in event_types

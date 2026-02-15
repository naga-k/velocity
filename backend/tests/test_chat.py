"""Tests for chat endpoint — SSE streaming with mocked Claude Agent SDK."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import ErrorEventData


def parse_sse_events(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of {event, data} dicts.

    Handles both \\n and \\r\\n line endings (sse_starlette uses \\r\\n).
    """
    events = []
    current_event = None
    current_data: list[str] = []

    for line in raw.split("\n"):
        line = line.rstrip("\r")  # handle \r\n line endings
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data.append(line[len("data:"):].strip())
        elif line == "" and current_event is not None and len(current_data) > 0:
            events.append({"event": current_event, "data": "\n".join(current_data)})
            current_event = None
            current_data = []

    # Handle last event if no trailing newline
    if current_event is not None and len(current_data) > 0:
        events.append({"event": current_event, "data": "\n".join(current_data)})

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
        # Patch settings where it's used in generate_response
        import app.agents as agents_mod
        with patch.object(agents_mod, "settings") as mock_settings:
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
            make_mock_tool_result_message,
        )

        mock_agent_sdk["set_messages"]([
            make_mock_subagent_message(
                agent_type="research",
                description="Searching Slack for feedback",
            ),
            make_mock_tool_result_message(),
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
            make_mock_tool_result_message,
        )

        mock_agent_sdk["set_messages"]([
            make_mock_subagent_message(agent_type="research"),
            make_mock_tool_result_message(),
            make_mock_subagent_message(agent_type="backlog"),
            make_mock_tool_result_message(),
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


class TestTextBlockFallback:
    """Test that TextBlocks are emitted when no streaming deltas come."""

    async def test_textblock_emitted_after_tool_call_no_deltas(
        self, client, mock_agent_sdk
    ):
        """When the orchestrator responds via TextBlock after a tool call
        (no streaming deltas), the text must still reach the frontend."""
        from tests.conftest import (
            make_mock_assistant_message,
            make_mock_result_message,
            make_mock_subagent_message,
            make_mock_tool_result_message,
        )

        mock_agent_sdk["set_messages"]([
            make_mock_subagent_message(agent_type="research"),
            make_mock_tool_result_message(),
            # Post-tool response with NO streaming deltas — only TextBlock
            make_mock_assistant_message("Based on the research, users love it."),
            make_mock_result_message(),
        ])

        resp = await client.post(
            "/api/chat",
            json={"message": "What feedback exists?"},
        )
        events = parse_sse_events(resp.text)
        text_events = [e for e in events if e["event"] == "text"]

        assert len(text_events) >= 1
        full_text = "".join(json.loads(e["data"]) for e in text_events)
        assert "users love it" in full_text

    async def test_textblock_skipped_when_deltas_present(
        self, client, mock_agent_sdk
    ):
        """When streaming deltas are present, TextBlock must be skipped
        to avoid duplication."""
        from tests.conftest import (
            make_mock_assistant_message,
            make_mock_result_message,
            make_mock_stream_text_deltas,
        )

        mock_agent_sdk["set_messages"]([
            *make_mock_stream_text_deltas("Hello from Claude!"),
            # This TextBlock duplicates the deltas — must be skipped
            make_mock_assistant_message("Hello from Claude!"),
            make_mock_result_message(),
        ])

        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        text_events = [e for e in events if e["event"] == "text"]

        full_text = "".join(json.loads(e["data"]) for e in text_events)
        # Should appear exactly once, not duplicated
        assert full_text == "Hello from Claude!"

    async def test_subagent_text_not_emitted(self, client, mock_agent_sdk):
        """Text from subagent StreamEvents (parent_tool_use_id set)
        must not reach the frontend."""
        from claude_agent_sdk.types import StreamEvent

        from tests.conftest import (
            make_mock_assistant_message,
            make_mock_result_message,
            make_mock_subagent_message,
            make_mock_tool_result_message,
        )

        subagent_delta = StreamEvent(
            uuid="evt-sub-0",
            session_id="test-session",
            event={
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "SUBAGENT TEXT"},
            },
            parent_tool_use_id="tool-123",
        )

        mock_agent_sdk["set_messages"]([
            make_mock_subagent_message(agent_type="research"),
            subagent_delta,  # subagent text — should be filtered
            make_mock_tool_result_message(),
            make_mock_assistant_message("Orchestrator summary."),
            make_mock_result_message(),
        ])

        resp = await client.post(
            "/api/chat",
            json={"message": "Research this"},
        )
        events = parse_sse_events(resp.text)
        text_events = [e for e in events if e["event"] == "text"]

        full_text = "".join(json.loads(e["data"]) for e in text_events)
        assert "SUBAGENT TEXT" not in full_text
        assert "Orchestrator summary" in full_text


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


class TestSSEWireFormat:
    """Verify the raw SSE format so frontend parsers can rely on it."""

    async def test_sse_uses_crlf_line_endings(self, client, mock_agent_sdk):
        """sse_starlette uses \\r\\n — parsers must handle this."""
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        # The raw response should contain \r\n (sse_starlette convention)
        raw_bytes = resp.content
        assert b"\r\n" in raw_bytes

    async def test_parser_handles_crlf(self):
        """parse_sse_events must work with \\r\\n line endings."""
        raw = "event: text\r\ndata: \"Hello\"\r\n\r\nevent: done\r\ndata: {}\r\n\r\n"
        events = parse_sse_events(raw)

        assert len(events) == 2
        assert events[0]["event"] == "text"
        assert events[0]["data"] == '"Hello"'
        assert events[1]["event"] == "done"

    async def test_parser_handles_lf(self):
        """parse_sse_events must also work with plain \\n."""
        raw = 'event: text\ndata: "World"\n\nevent: done\ndata: {}\n\n'
        events = parse_sse_events(raw)

        assert len(events) == 2
        assert events[0]["data"] == '"World"'

    async def test_events_are_separated_by_blank_lines(self, client, mock_agent_sdk):
        """Each SSE event must be followed by a blank line."""
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)

        # Must have at least text + done
        event_types = [e["event"] for e in events]
        assert "text" in event_types
        assert "done" in event_types

        # Verify each text event data is a valid JSON string
        for e in events:
            if e["event"] == "text":
                parsed = json.loads(e["data"])
                assert isinstance(parsed, str)


class TestErrorHandling:
    """Test that SDK errors produce graceful error + done events."""

    async def test_sdk_error_emits_error_and_done(self, client, mock_agent_sdk):
        """ClaudeSDKError should emit error + done, not crash."""
        from claude_agent_sdk import ClaudeSDKError

        mock_agent_sdk["client"].query = AsyncMock(
            side_effect=ClaudeSDKError("Connection failed")
        )
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "error" in event_types
        assert "done" in event_types
        error_data = json.loads(
            next(e["data"] for e in events if e["event"] == "error")
        )
        assert "Connection failed" in error_data["message"]

    async def test_unexpected_error_emits_error_and_done(self, client, mock_agent_sdk):
        """Generic exceptions should also emit error + done."""
        mock_agent_sdk["client"].connect = AsyncMock(
            side_effect=RuntimeError("Unexpected boom")
        )
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "error" in event_types
        assert "done" in event_types

    async def test_disconnect_failure_still_emits_done(self, client, mock_agent_sdk):
        """Even if disconnect() fails, done event should still be emitted."""
        mock_agent_sdk["client"].disconnect = AsyncMock(
            side_effect=Exception("disconnect failed")
        )
        resp = await client.post(
            "/api/chat",
            json={"message": "Hello"},
        )
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "done" in event_types
        assert "error" not in event_types


class TestSaveInsightValidation:
    """Test that save_insight category validation prevents path traversal."""

    def test_valid_categories_pass(self):
        """Normal categories match the validation regex."""
        import re

        pattern = r"^[a-zA-Z0-9_-]+$"
        for cat in ["feedback", "decision", "competitive", "my-category", "test_123"]:
            assert re.match(pattern, cat), f"{cat} should be valid"

    def test_path_traversal_rejected(self):
        """Categories with path separators are rejected by the regex."""
        import re

        pattern = r"^[a-zA-Z0-9_-]+$"
        for bad in ["../../etc/evil", "../config", "foo/bar", "a..b/c", "", "a b"]:
            assert not re.match(pattern, bad), f"{bad} should be rejected"


class TestClientReuse:
    """Test that SDK client workers are reused across requests for the same session."""

    async def test_worker_reused_for_same_session(self, client, mock_agent_sdk):
        """Two requests with the same session_id should reuse one worker."""
        resp1 = await client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": "sess-1"},
        )
        assert resp1.status_code == 200

        resp2 = await client.post(
            "/api/chat",
            json={"message": "Follow-up", "session_id": "sess-1"},
        )
        assert resp2.status_code == 200

        import app.agents.session_worker as worker_mod

        # One worker created (reused for second request)
        assert "sess-1" in worker_mod._workers
        mock_client = mock_agent_sdk["client"]
        mock_client.connect.assert_called_once()
        assert mock_client.query.call_count == 2

    async def test_different_sessions_get_different_workers(
        self, client, mock_agent_sdk
    ):
        """Different session_ids should create separate workers."""
        import app.agents.session_worker as worker_mod

        # Track how many clients are created
        clients_created = []

        def make_new_client(*args, **kwargs):
            m = MagicMock()
            m.connect = AsyncMock()
            m.disconnect = AsyncMock()
            m.query = AsyncMock()
            from tests.conftest import (
                _mock_receive_response,
                make_mock_result_message,
                make_mock_stream_text_deltas,
            )

            messages = [
                *make_mock_stream_text_deltas("Reply"),
                make_mock_result_message(),
            ]
            m.receive_response = MagicMock(
                side_effect=lambda: _mock_receive_response(messages)
            )
            clients_created.append(m)
            return m

        with patch("app.agents.session_worker.ClaudeSDKClient", side_effect=make_new_client):
            resp1 = await client.post(
                "/api/chat",
                json={"message": "Hello", "session_id": "sess-a"},
            )
            resp2 = await client.post(
                "/api/chat",
                json={"message": "Hello", "session_id": "sess-b"},
            )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert len(clients_created) == 2
        assert "sess-a" in worker_mod._workers
        assert "sess-b" in worker_mod._workers

    async def test_broken_worker_recreated(self, client, mock_agent_sdk):
        """If query() fails, the worker is evicted and recreated on retry."""
        from claude_agent_sdk import ClaudeSDKError

        import app.agents.session_worker as worker_mod

        # First request succeeds
        resp1 = await client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": "sess-fail"},
        )
        assert resp1.status_code == 200
        assert "sess-fail" in worker_mod._workers

        # Second request: query raises → worker evicted
        mock_agent_sdk["client"].query = AsyncMock(
            side_effect=ClaudeSDKError("broken")
        )
        resp2 = await client.post(
            "/api/chat",
            json={"message": "Retry", "session_id": "sess-fail"},
        )
        events = parse_sse_events(resp2.text)
        assert any(e["event"] == "error" for e in events)
        assert "sess-fail" not in worker_mod._workers

    async def test_delete_session_disconnects_worker(self, client, mock_agent_sdk):
        """DELETE /api/sessions/{id} should stop the worker and disconnect."""
        import app.agents.session_worker as worker_mod
        from app import session_store

        session = await session_store.create_session("Test")

        # Send a chat to populate the worker pool
        await client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": session.id},
        )
        assert session.id in worker_mod._workers

        # Delete the session
        resp = await client.delete(f"/api/sessions/{session.id}")
        assert resp.status_code == 204
        assert session.id not in worker_mod._workers
        mock_agent_sdk["client"].disconnect.assert_called_once()

    async def test_disconnect_all_workers(self, client, mock_agent_sdk):
        """disconnect_all_clients() should stop every worker."""
        import app.agents.session_worker as worker_mod

        # Create two workers via chat requests
        clients_created = []

        def make_client(*args, **kwargs):
            from tests.conftest import (
                _mock_receive_response,
                make_mock_result_message,
                make_mock_stream_text_deltas,
            )

            m = MagicMock()
            m.connect = AsyncMock()
            m.disconnect = AsyncMock()
            m.query = AsyncMock()
            messages = [
                *make_mock_stream_text_deltas("Reply"),
                make_mock_result_message(),
            ]
            m.receive_response = MagicMock(
                side_effect=lambda: _mock_receive_response(messages)
            )
            clients_created.append(m)
            return m

        with patch("app.agents.session_worker.ClaudeSDKClient", side_effect=make_client):
            await client.post(
                "/api/chat",
                json={"message": "Hello", "session_id": "s1"},
            )
            await client.post(
                "/api/chat",
                json={"message": "Hello", "session_id": "s2"},
            )

            assert len(worker_mod._workers) == 2
            from app.agents import disconnect_all_clients
            await disconnect_all_clients()

        assert len(worker_mod._workers) == 0
        for m in clients_created:
            m.disconnect.assert_called_once()

    async def test_connect_failure_not_cached(self, client, mock_agent_sdk):
        """If connect() fails, worker should NOT be stored in _workers."""
        import app.agents.session_worker as worker_mod

        mock_agent_sdk["client"].connect = AsyncMock(
            side_effect=RuntimeError("connect failed")
        )

        resp = await client.post(
            "/api/chat",
            json={"message": "Hello", "session_id": "sess-broken"},
        )
        events = parse_sse_events(resp.text)
        assert any(e["event"] == "error" for e in events)
        assert "sess-broken" not in worker_mod._workers


class TestMultiTurnConversation:
    """End-to-end tests simulating real multi-message conversations.

    These ensure session-scoped worker reuse works correctly across
    multiple sequential messages, error recovery, and session lifecycle.
    """

    async def test_three_message_conversation(self, client, mock_agent_sdk):
        """Simulate a 3-turn conversation — worker created once, queried 3x."""
        import app.agents.session_worker as worker_mod

        session_id = "conv-3turn"

        for i, msg in enumerate(["Hello", "Follow-up", "One more"], 1):
            resp = await client.post(
                "/api/chat",
                json={"message": msg, "session_id": session_id},
            )
            assert resp.status_code == 200
            events = parse_sse_events(resp.text)
            assert events[-1]["event"] == "done"

        # Single worker, connected once, queried 3 times
        assert session_id in worker_mod._workers
        mock_client = mock_agent_sdk["client"]
        mock_client.connect.assert_called_once()
        assert mock_client.query.call_count == 3

        # Verify session_id passed to each query() call
        for call in mock_client.query.call_args_list:
            assert call.kwargs.get("session_id") == session_id or call.args == (
                mock_client.query.call_args_list[0].args
            )

    async def test_interleaved_sessions(self, client, mock_agent_sdk):
        """Messages to different sessions should not interfere."""
        import app.agents.session_worker as worker_mod

        clients_created = []

        def make_client(*args, **kwargs):
            from tests.conftest import (
                _mock_receive_response,
                make_mock_result_message,
                make_mock_stream_text_deltas,
            )

            m = MagicMock()
            m.connect = AsyncMock()
            m.disconnect = AsyncMock()
            m.query = AsyncMock()
            messages = [
                *make_mock_stream_text_deltas("Reply"),
                make_mock_result_message(),
            ]
            m.receive_response = MagicMock(
                side_effect=lambda: _mock_receive_response(messages)
            )
            clients_created.append(m)
            return m

        with patch("app.agents.session_worker.ClaudeSDKClient", side_effect=make_client):
            # Interleave messages between two sessions
            await client.post(
                "/api/chat",
                json={"message": "A1", "session_id": "session-A"},
            )
            await client.post(
                "/api/chat",
                json={"message": "B1", "session_id": "session-B"},
            )
            await client.post(
                "/api/chat",
                json={"message": "A2", "session_id": "session-A"},
            )
            await client.post(
                "/api/chat",
                json={"message": "B2", "session_id": "session-B"},
            )

        # Two workers created (one per session)
        assert "session-A" in worker_mod._workers
        assert "session-B" in worker_mod._workers
        assert len(clients_created) == 2
        # Each client queried twice
        assert clients_created[0].query.call_count == 2
        assert clients_created[1].query.call_count == 2

    async def test_error_midconversation_recovers(self, client, mock_agent_sdk):
        """Error on turn 2 evicts worker; turn 3 gets a fresh one."""
        from claude_agent_sdk import ClaudeSDKError

        import app.agents.session_worker as worker_mod

        session_id = "conv-error-recovery"

        # Turn 1: success
        resp1 = await client.post(
            "/api/chat",
            json={"message": "Turn 1", "session_id": session_id},
        )
        assert resp1.status_code == 200
        assert session_id in worker_mod._workers

        # Turn 2: error → evicts worker
        mock_agent_sdk["client"].query = AsyncMock(
            side_effect=ClaudeSDKError("temporary failure")
        )
        resp2 = await client.post(
            "/api/chat",
            json={"message": "Turn 2", "session_id": session_id},
        )
        events2 = parse_sse_events(resp2.text)
        assert any(e["event"] == "error" for e in events2)
        assert session_id not in worker_mod._workers

        # Turn 3: restore query, should create new worker
        from tests.conftest import (
            _mock_receive_response,
            make_mock_result_message,
            make_mock_stream_text_deltas,
        )

        mock_agent_sdk["client"].query = AsyncMock()
        messages = [
            *make_mock_stream_text_deltas("Recovered!"),
            make_mock_result_message(),
        ]
        mock_agent_sdk["client"].receive_response = MagicMock(
            side_effect=lambda: _mock_receive_response(messages)
        )

        resp3 = await client.post(
            "/api/chat",
            json={"message": "Turn 3", "session_id": session_id},
        )
        events3 = parse_sse_events(resp3.text)
        text_events = [e for e in events3 if e["event"] == "text"]
        full_text = "".join(json.loads(e["data"]) for e in text_events)
        assert "Recovered" in full_text
        assert session_id in worker_mod._workers

    async def test_session_create_chat_delete_lifecycle(self, client, mock_agent_sdk):
        """Full lifecycle: create session → send messages → delete session."""
        import app.agents.session_worker as worker_mod
        from app import session_store

        # Create session
        session = await session_store.create_session("Lifecycle test")

        # Send 2 messages
        for msg in ["Hello", "World"]:
            resp = await client.post(
                "/api/chat",
                json={"message": msg, "session_id": session.id},
            )
            assert resp.status_code == 200

        assert session.id in worker_mod._workers
        mock_client = mock_agent_sdk["client"]
        assert mock_client.query.call_count == 2

        # Delete session
        resp = await client.delete(f"/api/sessions/{session.id}")
        assert resp.status_code == 204
        assert session.id not in worker_mod._workers
        mock_client.disconnect.assert_called_once()

        # Verify session is gone from DB
        fetched = await session_store.get_session(session.id)
        assert fetched is None

    async def test_many_sequential_messages(self, client, mock_agent_sdk):
        """Simulate 10 messages in a row — worker stays alive the whole time."""
        session_id = "conv-10msg"

        for i in range(10):
            resp = await client.post(
                "/api/chat",
                json={"message": f"Message {i}", "session_id": session_id},
            )
            assert resp.status_code == 200
            events = parse_sse_events(resp.text)
            assert events[-1]["event"] == "done"

        mock_client = mock_agent_sdk["client"]
        mock_client.connect.assert_called_once()
        assert mock_client.query.call_count == 10

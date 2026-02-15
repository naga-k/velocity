"""Shared test fixtures."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def setup_test_db(tmp_path):
    """Initialize a fresh SQLite database for each test."""
    from app.database import init_db
    import app.database as db_mod

    db_file = str(tmp_path / "test.db")
    with patch.object(db_mod, "settings") as mock_s:
        mock_s.database_url = f"sqlite:///{db_file}"
        await init_db()

    yield


@pytest.fixture(autouse=True)
async def setup_test_redis():
    """Provide a fake Redis instance for each test."""
    import app.redis_client as redis_mod

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    redis_mod._redis = fake
    yield
    await fake.aclose()
    redis_mod._redis = None


# ---------------------------------------------------------------------------
# Mock helpers for Claude Agent SDK
# ---------------------------------------------------------------------------


def make_mock_assistant_message(
    text: str = "Hello from Claude!",
    model: str = "claude-opus-4-6",
):
    """Create a mock AssistantMessage with a single TextBlock."""
    from claude_agent_sdk import AssistantMessage, TextBlock

    return AssistantMessage(
        content=[TextBlock(text=text)],
        model=model,
    )


def make_mock_result_message(
    input_tokens: int = 25,
    output_tokens: int = 10,
    session_id: str = "test-session",
):
    """Create a mock ResultMessage with usage data."""
    from claude_agent_sdk import ResultMessage

    return ResultMessage(
        subtype="result",
        duration_ms=500,
        duration_api_ms=400,
        is_error=False,
        num_turns=1,
        session_id=session_id,
        total_cost_usd=0.01,
        usage={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )


def make_mock_thinking_message(
    thinking_text: str = "Let me think about this...",
    response_text: str = "Here is my answer.",
    model: str = "claude-opus-4-6",
):
    """Create a mock AssistantMessage with ThinkingBlock + TextBlock."""
    from claude_agent_sdk import AssistantMessage, TextBlock, ThinkingBlock

    return AssistantMessage(
        content=[
            ThinkingBlock(thinking=thinking_text, signature="sig123"),
            TextBlock(text=response_text),
        ],
        model=model,
    )


def make_mock_subagent_message(
    agent_type: str = "research",
    description: str = "Searching Slack for context",
    model: str = "claude-opus-4-6",
):
    """Create a mock AssistantMessage with a Task tool call (subagent)."""
    from claude_agent_sdk import AssistantMessage, ToolUseBlock

    return AssistantMessage(
        content=[
            ToolUseBlock(
                id="tool-123",
                name="Task",
                input={
                    "subagent_type": agent_type,
                    "description": description,
                    "prompt": "Find relevant discussions",
                },
            ),
        ],
        model=model,
    )


def make_mock_tool_call_message(
    tool_name: str = "mcp__pm_tools__read_product_context",
    tool_input: dict | None = None,
    model: str = "claude-opus-4-6",
):
    """Create a mock AssistantMessage with a non-Task tool call."""
    from claude_agent_sdk import AssistantMessage, ToolUseBlock

    return AssistantMessage(
        content=[
            ToolUseBlock(
                id="tool-456",
                name=tool_name,
                input=tool_input or {},
            ),
        ],
        model=model,
    )


def make_mock_tool_result_message(
    tool_use_id: str = "tool-123",
    content: str = "Tool result here",
    model: str = "claude-opus-4-6",
):
    """Create a mock AssistantMessage with a ToolResultBlock."""
    from claude_agent_sdk import AssistantMessage, ToolResultBlock

    return AssistantMessage(
        content=[
            ToolResultBlock(
                tool_use_id=tool_use_id,
                content=content,
            ),
        ],
        model=model,
    )


def make_mock_stream_text_deltas(
    text: str = "Hello from Claude!",
    chunk_size: int = 5,
    session_id: str = "test-session",
):
    """Create a list of mock StreamEvents that simulate text streaming."""
    from claude_agent_sdk.types import StreamEvent

    events = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        events.append(
            StreamEvent(
                uuid=f"evt-{i}",
                session_id=session_id,
                event={
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": chunk},
                },
            )
        )
    return events


def make_mock_stream_thinking_delta(
    thinking_text: str = "Let me think...",
    session_id: str = "test-session",
):
    """Create a mock StreamEvent for a thinking delta."""
    from claude_agent_sdk.types import StreamEvent

    return StreamEvent(
        uuid="evt-think-0",
        session_id=session_id,
        event={
            "type": "content_block_delta",
            "delta": {"type": "thinking_delta", "thinking": thinking_text},
        },
    )


async def _mock_receive_response(messages):
    """Turn a list of messages into an async iterator."""
    for msg in messages:
        yield msg


@pytest.fixture
def mock_agent_sdk():
    """Patch ClaudeSDKClient to return canned responses.

    Yields a dict with the mock client and helper to set response messages.

    Usage:
        def test_chat(mock_agent_sdk):
            mock_agent_sdk["set_messages"]([
                make_mock_assistant_message("Hi!"),
                make_mock_result_message(),
            ])
    """
    messages = [
        *make_mock_stream_text_deltas("Hello from Claude!"),
        make_mock_result_message(),
    ]

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.receive_response = MagicMock(
        side_effect=lambda: _mock_receive_response(messages)
    )

    def set_messages(new_messages):
        nonlocal messages
        messages = new_messages
        mock_client.receive_response = MagicMock(
            side_effect=lambda: _mock_receive_response(messages)
        )

    import app.agents.session_worker as worker_mod

    with patch("app.agents.session_worker.ClaudeSDKClient", return_value=mock_client):
        with patch("app.agents.orchestrator.settings") as mock_settings:
            mock_settings.anthropic_configured = True
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model_opus = "claude-opus-4-6"
            mock_settings.anthropic_model_sonnet = "claude-sonnet-4-5-20250929"
            mock_settings.slack_configured = False
            mock_settings.linear_configured = False
            mock_settings.slack_bot_token = ""
            mock_settings.linear_api_key = ""
            mock_settings.max_budget_per_session_usd = 2.0
            mock_settings.max_turns = 30
            worker_mod._workers.clear()
            worker_mod._worker_locks.clear()
            yield {
                "client": mock_client,
                "set_messages": set_messages,
            }
            worker_mod._workers.clear()
            worker_mod._worker_locks.clear()

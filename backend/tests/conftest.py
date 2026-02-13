"""Shared test fixtures."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

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
def reset_sessions():
    """Clear in-memory session store between tests."""
    from app.routes.sessions import _sessions
    _sessions.clear()
    yield
    _sessions.clear()


def make_mock_stream_events(text: str = "Hello from Claude!"):
    """Create mock Anthropic streaming events for a simple text response.

    Returns a list of mock event objects that simulate the Anthropic
    messages.stream() async context manager.
    """
    events = []

    # message_start
    msg_start = MagicMock()
    msg_start.type = "message_start"
    msg_start.message = MagicMock()
    msg_start.message.usage = MagicMock()
    msg_start.message.usage.input_tokens = 25
    events.append(msg_start)

    # content_block_delta for each chunk
    for chunk in [text[:5], text[5:]]:
        delta_event = MagicMock()
        delta_event.type = "content_block_delta"
        delta_event.delta = MagicMock()
        delta_event.delta.text = chunk
        events.append(delta_event)

    # message_delta (usage)
    msg_delta = MagicMock()
    msg_delta.type = "message_delta"
    msg_delta.usage = MagicMock()
    msg_delta.usage.output_tokens = 10
    events.append(msg_delta)

    return events


@pytest.fixture
def mock_anthropic():
    """Patch anthropic.AsyncAnthropic to return canned streaming responses.

    Usage in tests:
        def test_chat(mock_anthropic):
            # mock_anthropic is already active
            ...
    """
    mock_events = make_mock_stream_events()

    async def async_event_iter():
        for event in mock_events:
            yield event

    mock_stream = MagicMock()
    mock_stream.__aiter__ = lambda self: async_event_iter()

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.messages.stream = MagicMock(return_value=mock_ctx)

    with patch("app.agent.anthropic.AsyncAnthropic", return_value=mock_client):
        with patch("app.agent.settings") as mock_settings:
            mock_settings.anthropic_configured = True
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model = "claude-sonnet-4-5-20250929"
            yield mock_client

"""SSE bridge — translates (event_type, json_data) tuples to ServerSentEvent objects.

This module sits between the agent layer and the HTTP response.
It never needs to change regardless of what powers the agent.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sse_starlette.sse import ServerSentEvent


async def stream_sse_events(
    event_source: AsyncGenerator[tuple[str, str], None],
) -> AsyncGenerator[ServerSentEvent, None]:
    """Convert (event_type, json_data) tuples to SSE events.

    Args:
        event_source: Async generator from agent.generate_response()
            yielding (event_type, json_data) tuples.

    Yields:
        ServerSentEvent objects ready for EventSourceResponse.
    """
    async for event_type, json_data in event_source:
        yield ServerSentEvent(
            event=event_type,
            data=json_data,
        )

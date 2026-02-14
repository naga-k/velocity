"""Agent layer — generates streaming responses.

The critical interface is `generate_response()`, an async generator that yields
`(event_type, event_data)` tuples. The SSE bridge and routes consume this
interface — they never need to change regardless of what powers the agent.

Scaffold: direct `anthropic` SDK streaming call (Sonnet).
Track A: replaces internals with Claude Agent SDK + ClaudeSDKClient.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import anthropic

from app.config import settings
from app.models import DoneEventData, ErrorEventData, TokenUsage

SYSTEM_PROMPT = """\
You are Velocity, an AI product management assistant for startup PMs.
You help PMs make better product decisions by analyzing data from their tools
(Linear, Slack, Notion) and providing grounded, evidence-based recommendations.

Be concise, actionable, and cite sources when available.
"""

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    """Return a singleton Anthropic client, created lazily."""
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def generate_response(
    message: str,
    session_id: str,
    context: dict | None = None,
) -> AsyncGenerator[tuple[str, str], None]:
    """Yield (event_type, json_data) tuples for an SSE stream.

    event_type is one of: "text", "error", "done"
    json_data is a JSON-encoded string ready for SSE `data:` field.

    For "text" events, json_data is a bare JSON string (e.g. '"hello"').
    For "error" and "done", json_data is a JSON object.
    """
    if not settings.anthropic_configured:
        yield (
            "error",
            ErrorEventData(
                message="Anthropic API key not configured",
                recoverable=False,
            ).model_dump_json(),
        )
        yield ("done", DoneEventData().model_dump_json())
        return

    client = _get_client()

    try:
        async with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        ) as stream:
            input_tokens = 0
            output_tokens = 0

            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield ("text", json.dumps(event.delta.text))

                elif event.type == "message_delta":
                    if hasattr(event.usage, "output_tokens"):
                        output_tokens = event.usage.output_tokens

                elif event.type == "message_start":
                    if hasattr(event.message, "usage"):
                        input_tokens = event.message.usage.input_tokens

            yield (
                "done",
                DoneEventData(
                    tokens_used=TokenUsage(
                        input=input_tokens,
                        output=output_tokens,
                    ),
                ).model_dump_json(),
            )

    except anthropic.APIError as e:
        yield (
            "error",
            ErrorEventData(
                message=f"Anthropic API error: {e.message}",
                recoverable=isinstance(e, anthropic.RateLimitError),
            ).model_dump_json(),
        )
        yield ("done", DoneEventData().model_dump_json())

"""Agent layer — generates streaming responses via Claude Agent SDK.

The critical interface is `generate_response()`, an async generator that yields
`(event_type, event_data)` tuples. The SSE bridge and routes consume this
interface — they never need to change regardless of what powers the agent.

Track A: Claude Agent SDK with ClaudeSDKClient, subagents, and MCP servers.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKError,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from claude_agent_sdk.types import StreamEvent

from app.config import settings
from app.models import (
    AgentActivityData,
    DoneEventData,
    ErrorEventData,
    ThinkingEventData,
    TokenUsage,
    ToolCallData,
)

from .session_worker import (
    disconnect_all_clients,
    get_or_create_worker,
    remove_session_client,
)

logger = logging.getLogger(__name__)

# Re-export public interface
__all__ = ["generate_response", "remove_session_client", "disconnect_all_clients"]


# ---------------------------------------------------------------------------
# The critical interface — must stay identical
# ---------------------------------------------------------------------------


async def generate_response(
    message: str,
    session_id: str,
    context: dict | None = None,
) -> AsyncGenerator[tuple[str, str], None]:
    """Yield (event_type, json_data) tuples for an SSE stream.

    event_type is one of: "text", "thinking", "agent_activity", "tool_call",
    "error", "done".
    json_data is a JSON-encoded string ready for SSE `data:` field.
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

    agents_used: list[str] = []
    done_emitted = False

    try:
        worker = await get_or_create_worker(session_id)

        # Track whether we've emitted text via StreamEvent deltas for
        # the current "segment" (between tool calls). When the SDK
        # streams deltas, AssistantMessage TextBlocks duplicate them —
        # we skip those. But after tool calls, the SDK may NOT stream
        # deltas, so we must emit the TextBlock as fallback.
        has_streamed_text = False
        inside_tool_call = False

        async for msg in worker.query_and_stream(message, session_id):
            # --- Full assistant messages (content blocks) ---
            if isinstance(msg, AssistantMessage):
                # A new AssistantMessage means any previous tool call
                # has completed (SDK handles execution internally and
                # does NOT yield ToolResultBlock). Reset the flag so
                # post-tool text can flow through.
                inside_tool_call = False

                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # Emit only if no deltas were streamed for this
                        # segment (avoids duplicate text)
                        if not has_streamed_text and not inside_tool_call:
                            yield ("text", json.dumps(block.text))
                        has_streamed_text = False

                    elif isinstance(block, ToolUseBlock):
                        has_streamed_text = False
                        inside_tool_call = True
                        # Detect subagent invocations
                        if block.name == "Task":
                            agent_type = block.input.get(
                                "subagent_type", "unknown"
                            )
                            if agent_type not in agents_used:
                                agents_used.append(agent_type)
                            yield (
                                "agent_activity",
                                AgentActivityData(
                                    agent=agent_type,
                                    status="running",
                                    task=block.input.get("description", ""),
                                ).model_dump_json(),
                            )
                        else:
                            yield (
                                "tool_call",
                                ToolCallData(
                                    tool=block.name,
                                    params=block.input,
                                ).model_dump_json(),
                            )

                    elif isinstance(block, ToolResultBlock):
                        inside_tool_call = False
                        has_streamed_text = False

            # --- Streaming partial events ---
            elif isinstance(msg, StreamEvent):
                event = msg.event
                event_type = event.get("type", "")

                # Only stream orchestrator text, not subagent text
                if event_type == "content_block_delta" and not msg.parent_tool_use_id:
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        has_streamed_text = True
                        yield ("text", json.dumps(delta.get("text", "")))
                    elif delta.get("type") == "thinking_delta":
                        yield (
                            "thinking",
                            ThinkingEventData(
                                text=delta.get("thinking", ""),
                            ).model_dump_json(),
                        )

            # --- Final result with cost/usage ---
            elif isinstance(msg, ResultMessage):
                done_emitted = True
                usage = msg.usage or {}
                yield (
                    "done",
                    DoneEventData(
                        tokens_used=TokenUsage(
                            input=usage.get("input_tokens", 0),
                            output=usage.get("output_tokens", 0),
                        ),
                        agents_used=agents_used,
                    ).model_dump_json(),
                )

    except ClaudeSDKError as e:
        logger.error("Claude SDK error: %s", e)
        await remove_session_client(session_id)
        yield (
            "error",
            ErrorEventData(
                message=f"Agent error: {e}",
                recoverable=False,
            ).model_dump_json(),
        )

    except Exception as e:
        logger.exception("Unexpected error in generate_response")
        await remove_session_client(session_id)
        yield (
            "error",
            ErrorEventData(
                message=f"Unexpected error: {e}",
                recoverable=False,
            ).model_dump_json(),
        )

    finally:
        if not done_emitted:
            yield ("done", DoneEventData(agents_used=agents_used).model_dump_json())

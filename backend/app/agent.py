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
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ClaudeSDKError,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import StreamEvent, ThinkingConfigAdaptive

from app.config import settings
from app.models import (
    AgentActivityData,
    DoneEventData,
    ErrorEventData,
    ThinkingEventData,
    TokenUsage,
    ToolCallData,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"

# ---------------------------------------------------------------------------
# System prompt for the orchestrator (Opus)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are Velocity, an AI product management assistant for startup PMs.

You have access to specialized subagents — use them when the user's request
requires external data:

- **research**: Search Slack conversations, the web, and other sources for
  context, feedback, and background information.
- **backlog**: Read project state from Linear — tickets, sprints, blockers,
  velocity metrics.
- **prioritization**: Rank and score items using frameworks like RICE or
  impact-effort. Works with outputs from research and backlog agents.
- **doc-writer**: Generate PRDs, stakeholder updates, sprint summaries, and
  other grounded documents.

When a task requires multiple types of information, run subagents in parallel
when possible. Always ground your responses in real data from integrations.
Cite sources. Be concise, actionable, and opinionated — but transparent about
uncertainty.

You also have PM memory tools:
- **read_product_context**: Load the current product overview and accumulated
  knowledge.
- **save_insight**: Persist a new product insight for future sessions.
"""

# ---------------------------------------------------------------------------
# Custom PM tools (in-process MCP server)
# ---------------------------------------------------------------------------


@tool(
    "read_product_context",
    "Read the current product context and accumulated knowledge",
    {},
)
async def read_product_context(args: dict) -> dict:
    """Load product-context.md from the memory directory."""
    context_path = MEMORY_DIR / "product-context.md"
    if context_path.exists():
        text = context_path.read_text()
    else:
        text = "(No product context file found.)"
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "save_insight",
    "Save a product insight to persistent memory",
    {
        "category": str,  # "feedback" | "decision" | "metric" | "competitive"
        "content": str,
        "sources": str,  # comma-separated source URLs
    },
)
async def save_insight(args: dict) -> dict:
    """Append an insight to the appropriate category file."""
    category = args["category"]
    insights_dir = MEMORY_DIR / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)
    target = insights_dir / f"{category}.md"
    with open(target, "a") as f:
        f.write(f"\n---\n{args['content']}\nSources: {args['sources']}\n")
    return {"content": [{"type": "text", "text": f"Insight saved to {category}"}]}


_pm_tools_server = create_sdk_mcp_server(
    name="pm_tools",
    tools=[read_product_context, save_insight],
)

# ---------------------------------------------------------------------------
# Subagent definitions
# ---------------------------------------------------------------------------

AGENTS: dict[str, AgentDefinition] = {
    "research": AgentDefinition(
        description=(
            "Research specialist. Use for finding discussions, feedback, and "
            "context from Slack, web, and other sources. Use when the user asks "
            "about what people are saying, what feedback exists, or needs "
            "background research."
        ),
        prompt=(
            "You are a research agent for a PM team. Find and synthesize "
            "information from Slack, web, and other sources.\n"
            "Return structured findings with sources. Be thorough but concise. "
            "Always cite where information came from."
        ),
        model="sonnet",
    ),
    "backlog": AgentDefinition(
        description=(
            "Backlog analyst. Use for reading project state from Linear: "
            "current sprint, tickets, blockers, velocity. Use when the user "
            "asks about what's in the backlog, sprint status, or ticket details."
        ),
        prompt=(
            "You are a backlog analyst. Read and structure project state from "
            "Linear.\nSummarize ticket status, blockers, velocity, and key "
            "metrics. Always include ticket URLs."
        ),
        model="sonnet",
    ),
    "prioritization": AgentDefinition(
        description=(
            "Prioritization expert. Use when the user needs help ranking, "
            "scoring, or deciding between options. Works with outputs from "
            "other agents to apply RICE, impact-effort, or custom scoring."
        ),
        prompt=(
            "You are a prioritization expert. Given research findings and "
            "backlog state, help rank and score items.\n"
            "Apply RICE or impact-effort frameworks. Cite evidence for and "
            "against each option. Flag trade-offs and open questions.\n"
            "Be opinionated but transparent about uncertainty."
        ),
        model="opus",
    ),
    "doc-writer": AgentDefinition(
        description=(
            "Document generator. Use for creating PRDs, stakeholder updates, "
            "one-pagers, sprint summaries. Produces publication-ready markdown "
            "with citations."
        ),
        prompt=(
            "You are a document specialist for a PM team. Generate "
            "well-structured, grounded documents.\n"
            "Include citations for all claims. Write for the specified "
            "audience. Keep it concise and actionable."
        ),
        model="opus",
    ),
}

# ---------------------------------------------------------------------------
# SDK client factory
# ---------------------------------------------------------------------------


def _build_mcp_servers() -> dict:
    """Build the MCP server config dict based on available credentials."""
    servers: dict = {
        "pm_tools": _pm_tools_server,
    }

    if settings.slack_configured:
        servers["slack"] = {
            "command": "npx",
            "args": ["@anthropic/slack-mcp"],
            "env": {"SLACK_BOT_TOKEN": settings.slack_bot_token},
        }

    if settings.linear_configured:
        servers["linear"] = {
            "command": "npx",
            "args": ["@anthropic/linear-mcp"],
            "env": {"LINEAR_API_KEY": settings.linear_api_key},
        }

    return servers


def _build_options() -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for the PM orchestrator."""
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=settings.anthropic_model_opus,
        agents=AGENTS,
        mcp_servers=_build_mcp_servers(),
        allowed_tools=[
            "Task",  # subagent invocation
            "mcp__pm_tools__read_product_context",
            "mcp__pm_tools__save_insight",
        ],
        permission_mode="bypassPermissions",
        max_turns=settings.max_turns,
        max_budget_usd=settings.max_budget_per_session_usd,
        include_partial_messages=True,
        thinking=ThinkingConfigAdaptive(type="adaptive"),
        cwd=str(MEMORY_DIR.parent),
        env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
    )


# NOTE: We create a fresh ClaudeSDKClient per query instead of caching
# per-session. This avoids SDK bug #558 where the second query hangs
# after the first invokes a subagent Task. Multi-turn context is not
# preserved across queries for now — revisit when the SDK fixes this.


async def cleanup_all_sessions() -> None:
    """No-op — clients are cleaned up per-query now."""
    pass


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

    try:
        # Create a fresh client per query to avoid SDK bug #558 where
        # the second query hangs after the first invokes a subagent Task.
        client = ClaudeSDKClient(options=_build_options())
        await client.connect()
        await client.query(message)

        # Track whether we've emitted text via StreamEvent deltas for
        # the current "segment" (between tool calls). When the SDK
        # streams deltas, AssistantMessage TextBlocks duplicate them —
        # we skip those. But after tool calls, the SDK may NOT stream
        # deltas, so we must emit the TextBlock as fallback.
        has_streamed_text = False
        inside_tool_call = False

        async for msg in client.receive_response():
            # --- Full assistant messages (content blocks) ---
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # Emit only if no deltas were streamed for this
                        # segment AND we're not inside a subagent call
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

        # Clean up the per-query client
        try:
            await client.disconnect()
        except Exception:
            logger.warning("Error disconnecting client for session %s", session_id)

    except ClaudeSDKError as e:
        logger.error("Claude SDK error: %s", e)
        yield (
            "error",
            ErrorEventData(
                message=f"Agent error: {e}",
                recoverable=False,
            ).model_dump_json(),
        )
        yield ("done", DoneEventData(agents_used=agents_used).model_dump_json())

    except Exception as e:
        logger.exception("Unexpected error in generate_response")
        yield (
            "error",
            ErrorEventData(
                message=f"Unexpected error: {e}",
                recoverable=False,
            ).model_dump_json(),
        )
        yield ("done", DoneEventData(agents_used=agents_used).model_dump_json())

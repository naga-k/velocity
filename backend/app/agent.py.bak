"""Agent layer — generates streaming responses via Claude Agent SDK.

The critical interface is `generate_response()`, an async generator that yields
`(event_type, event_data)` tuples. The SSE bridge and routes consume this
interface — they never need to change regardless of what powers the agent.

Track A: Claude Agent SDK with ClaudeSDKClient, subagents, and MCP servers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ClaudeSDKError,
    ResultMessage,
    TextBlock,
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
    if not re.match(r"^[a-zA-Z0-9_-]+$", category):
        return {"content": [{"type": "text", "text": f"Invalid category: {category}"}]}
    insights_dir = MEMORY_DIR / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)
    target = insights_dir / f"{category}.md"
    with open(target, "a") as f:
        f.write(f"\n---\n{args['content']}\nSources: {args['sources']}\n")
    return {"content": [{"type": "text", "text": f"Insight saved to {category}"}]}


@tool(
    "create_linear_issue",
    "Create a new Linear issue/ticket with title, description, assignee, priority",
    {
        "title": str,  # Issue title (required)
        "description": str,  # Issue description (optional)
        "priority": int,  # Priority 0-4: 0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low
    },
)
async def create_linear_issue(args: dict) -> dict:
    """Create a new Linear issue via GraphQL mutation."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    title = args.get("title")
    if not title:
        return {"content": [{"type": "text", "text": "Title is required"}]}

    description = args.get("description", "")
    priority = args.get("priority", 0)

    # Get the first team
    teams_query = "query { teams { nodes { id name } } }"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": teams_query},
                headers={"Authorization": settings.linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            teams = data.get("data", {}).get("teams", {}).get("nodes", [])
            if not teams:
                return {"content": [{"type": "text", "text": "No teams found"}]}
            team_id = teams[0]["id"]
    except Exception as e:
        logger.exception("Error fetching teams")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

    # Escape description for GraphQL
    escaped_desc = description.replace('"', '\\"').replace("\n", "\\n")

    mutation = f"""
    mutation {{
      issueCreate(input: {{
        teamId: "{team_id}"
        title: "{title}"
        description: "{escaped_desc}"
        priority: {priority}
      }}) {{
        success
        issue {{
          id
          identifier
          title
          url
          state {{ name }}
        }}
      }}
    }}
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation},
                headers={"Authorization": settings.linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return {
                    "content": [
                        {"type": "text", "text": f"Linear API error: {data['errors']}"}
                    ]
                }

            result = data.get("data", {}).get("issueCreate", {})
            if result.get("success"):
                issue = result.get("issue", {})
                msg = f"✅ Created issue [{issue['identifier']}]({issue['url']}): {issue['title']}\n"
                msg += f"State: {issue['state']['name']}"
                return {"content": [{"type": "text", "text": msg}]}
            else:
                return {"content": [{"type": "text", "text": "Failed to create issue"}]}
    except Exception as e:
        logger.exception("Error creating Linear issue")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "update_linear_issue",
    "Update an existing Linear issue - assign to engineer, change priority, update status",
    {
        "issue_id": str,  # Issue ID or identifier (e.g., "VEL-123")
        "assignee_email": str,  # Email of user to assign (optional)
        "priority": int,  # New priority 0-4 (optional)
        "state_name": str,  # New state like "In Progress", "Done" (optional)
        "title": str,  # New title (optional)
        "description": str,  # New description (optional)
    },
)
async def update_linear_issue(args: dict) -> dict:
    """Update a Linear issue via GraphQL mutation."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    issue_id = args.get("issue_id")
    if not issue_id:
        return {"content": [{"type": "text", "text": "issue_id is required"}]}

    assignee_email = args.get("assignee_email")
    priority = args.get("priority")
    state_name = args.get("state_name")
    title = args.get("title")
    description = args.get("description")

    # Build update input
    updates = []

    if title:
        updates.append(f'title: "{title}"')

    if description:
        escaped_desc = description.replace('"', '\\"').replace("\n", "\\n")
        updates.append(f'description: "{escaped_desc}"')

    if priority is not None:
        updates.append(f'priority: {priority}')

    # Get assignee ID from email
    if assignee_email:
        users_query = f"""
        query {{
          users(filter: {{ email: {{ eq: "{assignee_email}" }} }}) {{
            nodes {{ id name email }}
          }}
        }}
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": users_query},
                    headers={"Authorization": settings.linear_api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                users = data.get("data", {}).get("users", {}).get("nodes", [])
                if users:
                    updates.append(f'assigneeId: "{users[0]["id"]}"')
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"User with email {assignee_email} not found",
                            }
                        ]
                    }
        except Exception as e:
            logger.exception("Error fetching user")
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

    # Get state ID from name
    if state_name:
        states_query = """
        query {
          workflowStates {
            nodes { id name }
          }
        }
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": states_query},
                    headers={"Authorization": settings.linear_api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                states = data.get("data", {}).get("workflowStates", {}).get("nodes", [])
                matching_state = next(
                    (s for s in states if s["name"].lower() == state_name.lower()), None
                )
                if matching_state:
                    updates.append(f'stateId: "{matching_state["id"]}"')
                else:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"State '{state_name}' not found",
                            }
                        ]
                    }
        except Exception as e:
            logger.exception("Error fetching states")
            return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}

    if not updates:
        return {"content": [{"type": "text", "text": "No updates specified"}]}

    mutation = f"""
    mutation {{
      issueUpdate(id: "{issue_id}", input: {{ {", ".join(updates)} }}) {{
        success
        issue {{
          id
          identifier
          title
          url
          state {{ name }}
          assignee {{ name email }}
          priority
        }}
      }}
    }}
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation},
                headers={"Authorization": settings.linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return {
                    "content": [
                        {"type": "text", "text": f"Linear API error: {data['errors']}"}
                    ]
                }

            result = data.get("data", {}).get("issueUpdate", {})
            if result.get("success"):
                issue = result.get("issue", {})
                msg = f"✅ Updated issue [{issue['identifier']}]({issue['url']})\n"
                msg += f"Title: {issue['title']}\n"
                msg += f"State: {issue['state']['name']}\n"
                if issue.get("assignee"):
                    msg += f"Assigned to: {issue['assignee']['name']} ({issue['assignee']['email']})\n"
                msg += f"Priority: {issue.get('priority', 0)}"
                return {"content": [{"type": "text", "text": msg}]}
            else:
                return {"content": [{"type": "text", "text": "Failed to update issue"}]}
    except Exception as e:
        logger.exception("Error updating Linear issue")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "list_linear_issues",
    "Get issues from Linear backlog with optional filtering",
    {
        "limit": int,  # Number of issues to return (default 20)
        "filter": str,  # Optional filter: "active", "backlog", "all" (default "active")
    },
)
async def list_linear_issues(args: dict) -> dict:
    """Query Linear issues via GraphQL API."""
    import httpx

    if not settings.linear_configured:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    limit = args.get("limit", 20)
    filter_type = args.get("filter", "active")

    # Build GraphQL query
    filter_clause = ""
    if filter_type == "active":
        filter_clause = ', filter: { state: { type: { nin: ["completed", "canceled"] } } }'
    elif filter_type == "backlog":
        filter_clause = ', filter: { state: { type: { eq: "backlog" } } }'

    query = f"""
    query {{
      issues(first: {limit}{filter_clause}) {{
        nodes {{
          id
          identifier
          title
          description
          state {{ name }}
          priority
          assignee {{ name }}
          createdAt
          updatedAt
          url
        }}
      }}
    }}
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": query},
                headers={"Authorization": settings.linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Linear API error: {data['errors']}",
                        }
                    ]
                }

            issues = data.get("data", {}).get("issues", {}).get("nodes", [])
            if not issues:
                return {"content": [{"type": "text", "text": "No issues found"}]}

            # Format as markdown
            result = f"# Linear Issues ({filter_type})\n\n"
            for issue in issues:
                result += f"## [{issue['identifier']}]({issue['url']}) {issue['title']}\n"
                result += f"- **State**: {issue['state']['name']}\n"
                result += f"- **Priority**: {issue.get('priority', 'None')}\n"
                if issue.get("assignee"):
                    result += f"- **Assignee**: {issue['assignee']['name']}\n"
                if issue.get("description"):
                    desc = issue["description"][:200]
                    result += f"- **Description**: {desc}...\n"
                result += "\n"

            return {"content": [{"type": "text", "text": result}]}
    except Exception as e:
        logger.exception("Error fetching Linear issues")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


_pm_tools_server = create_sdk_mcp_server(
    name="pm_tools",
    tools=[
        read_product_context,
        save_insight,
        list_linear_issues,
        create_linear_issue,
        update_linear_issue,
    ],
)

# ---------------------------------------------------------------------------
# Agent tool specialization
# ---------------------------------------------------------------------------
# Each agent gets specific tools to enforce separation of concerns.
# Tool names follow the pattern: mcp__{server}__{tool}

AGENT_TOOLS = {
    "research": [
        # Slack integration tools (if configured)
        "mcp__slack__message_search",
        "mcp__slack__get_channel",
        "mcp__slack__get_thread",
        # Web search and fetch
        "WebSearch",
        "WebFetch",
        # File reading for context
        "Read",
        "Grep",
    ],
    "backlog": [
        # Linear integration (custom tools)
        "mcp__pm_tools__list_linear_issues",
        "mcp__pm_tools__create_linear_issue",
        "mcp__pm_tools__update_linear_issue",
        # File operations for local ticket data
        "Read",
        "Glob",
    ],
    "prioritization": [
        # No external integrations — pure analysis
        "Read",
        "Grep",
    ],
    "doc-writer": [
        # Product context and insights
        "mcp__pm_tools__read_product_context",
        "mcp__pm_tools__save_insight",
        # All integration data for citations
        "mcp__pm_tools__list_linear_issues",
        "mcp__pm_tools__create_linear_issue",
        "mcp__pm_tools__update_linear_issue",
        "mcp__slack__message_search",
        "WebSearch",
        "WebFetch",
        # File operations for document generation
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
    ],
}

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
        tools=AGENT_TOOLS["research"],
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
        tools=AGENT_TOOLS["backlog"],
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
        tools=AGENT_TOOLS["prioritization"],
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
        tools=AGENT_TOOLS["doc-writer"],
        model="opus",
    ),
}


# ---------------------------------------------------------------------------
# Session worker — runs SDK client in a persistent background task
# ---------------------------------------------------------------------------
#
# The Claude Agent SDK's ClaudeSDKClient uses an internal anyio task group
# that is created during connect(). All SDK operations (query, receive_response)
# must happen in the SAME asyncio task as connect(). FastAPI handles each HTTP
# request in a separate ASGI task, so we can't call receive_response() on a
# client that was connected in a previous request's task.
#
# Solution: each session gets a dedicated asyncio.Task ("worker") that owns
# the SDK client. HTTP request handlers communicate with the worker via
# asyncio.Queues. The worker stays in the same task context for the client's
# entire lifetime.
# ---------------------------------------------------------------------------

_SENTINEL = object()  # Marks end of a response stream


class _SessionWorker:
    """Manages an SDK client in a dedicated asyncio.Task.

    The background task runs connect() and then loops: receive a query from
    the input queue, call query() + receive_response(), push each SDK message
    to the output queue, push a sentinel when done.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._input: asyncio.Queue[
            tuple[str, str, asyncio.Queue[Any]] | None
        ] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._started = asyncio.Event()
        self._connect_error: Exception | None = None

    async def start(self) -> None:
        """Launch the background worker task."""
        self._task = asyncio.create_task(
            self._run(), name=f"session-worker-{self.session_id}"
        )
        # Wait until the worker signals it's connected (or failed)
        await self._started.wait()
        if self._connect_error is not None:
            raise self._connect_error

    async def _run(self) -> None:
        """Background loop: connect client, then serve queries."""
        # Prevent nested session detection
        os.environ.pop("CLAUDECODE", None)

        client = ClaudeSDKClient(options=_build_options())
        try:
            await client.connect()
            self._started.set()

            while True:
                item = await self._input.get()
                if item is None:
                    break  # shutdown

                message, sid, out_q = item
                try:
                    await client.query(message, session_id=sid)
                    async for msg in client.receive_response():
                        await out_q.put(msg)
                except Exception as exc:
                    try:
                        await out_q.put(exc)
                    except Exception:
                        logger.error(
                            "Failed to enqueue exception for session %s",
                            self.session_id,
                        )
                finally:
                    try:
                        await out_q.put(_SENTINEL)
                    except Exception:
                        logger.error(
                            "Failed to enqueue sentinel for session %s",
                            self.session_id,
                        )

        except Exception as exc:
            logger.exception("Session worker %s crashed", self.session_id)
            self._connect_error = exc
            self._started.set()  # unblock start() if connect failed
        finally:
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(
                    "Error disconnecting client for session %s: %s",
                    self.session_id,
                    e,
                )

    async def query_and_stream(
        self, message: str, session_id: str
    ) -> AsyncGenerator[Any, None]:
        """Send a query and yield SDK messages from the worker."""
        out_q: asyncio.Queue[Any] = asyncio.Queue()
        await self._input.put((message, session_id, out_q))
        while True:
            msg = await out_q.get()
            if msg is _SENTINEL:
                break
            if isinstance(msg, Exception):
                raise msg
            yield msg

    async def stop(self) -> None:
        """Signal the worker to shut down and wait for it."""
        await self._input.put(None)
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(
                    "Session worker %s did not stop in time, cancelling",
                    self.session_id,
                )
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass


# ---------------------------------------------------------------------------
# Session worker pool
# ---------------------------------------------------------------------------

_workers: dict[str, _SessionWorker] = {}
_worker_locks: dict[str, asyncio.Lock] = {}


async def _get_or_create_worker(session_id: str) -> _SessionWorker:
    """Return an existing worker for this session, or create and start one."""
    if session_id in _workers:
        return _workers[session_id]

    # Per-session lock prevents duplicate workers from concurrent requests
    if session_id not in _worker_locks:
        _worker_locks[session_id] = asyncio.Lock()

    async with _worker_locks[session_id]:
        # Double-check after acquiring lock
        if session_id in _workers:
            return _workers[session_id]

        worker = _SessionWorker(session_id)
        await worker.start()
        _workers[session_id] = worker
        return worker


async def remove_session_client(session_id: str) -> None:
    """Stop and remove the worker for a session."""
    _worker_locks.pop(session_id, None)
    worker = _workers.pop(session_id, None)
    if worker is not None:
        try:
            await worker.stop()
        except Exception:
            logger.warning("Error stopping worker for session %s", session_id)


async def disconnect_all_clients() -> None:
    """Stop all active workers. Called on server shutdown."""
    for sid in list(_workers.keys()):
        await remove_session_client(sid)


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
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "env": {
                "SLACK_BOT_TOKEN": settings.slack_bot_token,
                "SLACK_TEAM_ID": settings.slack_team_id,
            },
        }

    # Linear tools now implemented as custom tools in _pm_tools_server
    # if settings.linear_configured:
    #     servers["linear"] = {
    #         "command": "npx",
    #         "args": ["-y", "mcp-remote", "https://mcp.linear.app/mcp"],
    #         "env": {"LINEAR_API_KEY": settings.linear_api_key},
    #     }

    return servers


def _stderr_callback(line: str) -> None:
    """Capture CLI subprocess stderr for debugging."""
    logger.warning("CLI stderr: %s", line)


def _build_options() -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for the PM orchestrator."""
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=settings.anthropic_model_opus,
        agents=AGENTS,
        mcp_servers=_build_mcp_servers(),
        permission_mode="bypassPermissions",
        max_turns=settings.max_turns,
        max_budget_usd=settings.max_budget_per_session_usd,
        include_partial_messages=True,
        thinking=ThinkingConfigAdaptive(type="adaptive"),
        cwd=str(MEMORY_DIR.parent),
        env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
        stderr=_stderr_callback,
    )


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
        worker = await _get_or_create_worker(session_id)

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

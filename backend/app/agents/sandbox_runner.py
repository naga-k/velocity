#!/usr/bin/env python
"""Sandbox runner for Claude Agent SDK execution.

This script is uploaded to Daytona sandboxes and executed to run the full
agent orchestration loop. It emits JSON events to stdout that are parsed
by the session worker in the FastAPI application.

Usage:
    python sandbox_runner.py \\
        --message "What's in our current sprint?" \\
        --session-id "sess-123" \\
        --anthropic-api-key "sk-..." \\
        --config '{"max_turns": 30, "max_budget_usd": 2.0}'
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import ThinkingConfigAdaptive

# Configure logging to stderr (stdout is for JSON events)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON Event Emission
# ---------------------------------------------------------------------------


def emit_event(event_type: str, data: dict) -> None:
    """Emit a JSON event to stdout for parsing by session worker."""
    event = {"type": event_type, **data}
    print(json.dumps(event), flush=True)


def emit_error(message: str, recoverable: bool = False) -> None:
    """Emit an error event."""
    emit_event("error", {"message": message, "recoverable": recoverable})


def emit_done(tokens_used: dict | None = None, agents_used: list | None = None) -> None:
    """Emit a done event."""
    emit_event(
        "done",
        {
            "tokens_used": tokens_used or {"input": 0, "output": 0},
            "agents_used": agents_used or [],
        },
    )


# ---------------------------------------------------------------------------
# Tool Implementations (Simplified for Sandbox)
# ---------------------------------------------------------------------------
# Product context and memory files don't exist in ephemeral sandboxes,
# so these tools return empty/placeholder responses.


@tool(
    "read_product_context",
    "Load the current product context from memory",
    {},
)
async def read_product_context(args: dict) -> dict:
    """Return empty product context (files don't exist in sandbox)."""
    return {
        "content": [
            {
                "type": "text",
                "text": "Product context not available in sandbox environment",
            }
        ]
    }


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
    """Acknowledge insight save (no actual persistence in sandbox)."""
    category = args.get("category", "unknown")
    return {
        "content": [
            {
                "type": "text",
                "text": f"Insight saved to {category} (sandbox mode - not persisted)",
            }
        ]
    }


# ---------------------------------------------------------------------------
# Linear Tools (Keep full implementation - makes HTTP requests)
# ---------------------------------------------------------------------------
# These work in sandbox because they make HTTP requests to Linear API,
# not file operations.


@tool(
    "list_linear_issues",
    "List Linear issues with optional filtering",
    {
        "limit": int,  # Max number of issues to return (default 20)
        "filter": str,  # Optional GraphQL filter expression
    },
)
async def list_linear_issues(args: dict) -> dict:
    """List Linear issues via GraphQL query."""
    import httpx
    import os

    linear_api_key = os.getenv("LINEAR_API_KEY")
    if not linear_api_key:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    limit = args.get("limit", 20)

    query = """
    query ListIssues($first: Int!) {
      issues(first: $first, orderBy: updatedAt) {
        nodes {
          id
          identifier
          title
          description
          priority
          priorityLabel
          state { name }
          assignee { name email }
          createdAt
          updatedAt
          url
        }
      }
    }
    """

    variables = {"first": limit}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": query, "variables": variables},
                headers={"Authorization": linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            issues = data.get("data", {}).get("issues", {}).get("nodes", [])
            if not issues:
                return {"content": [{"type": "text", "text": "No issues found"}]}

            # Format as markdown
            lines = ["# Linear Issues\n"]
            for issue in issues:
                lines.append(f"## {issue['identifier']}: {issue['title']}")
                lines.append(f"- **Status**: {issue['state']['name']}")
                lines.append(f"- **Priority**: {issue.get('priorityLabel', 'None')}")
                assignee = issue.get("assignee")
                if assignee:
                    lines.append(f"- **Assignee**: {assignee['name']}")
                lines.append(f"- **URL**: {issue['url']}")
                if issue.get("description"):
                    desc = issue["description"][:200]
                    lines.append(f"- **Description**: {desc}...")
                lines.append("")

            return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    except Exception as e:
        logger.exception("Error fetching Linear issues")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "create_linear_issue",
    "Create a new Linear issue/ticket",
    {
        "title": str,
        "description": str,
        "priority": int,  # 0-4: 0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low
    },
)
async def create_linear_issue(args: dict) -> dict:
    """Create a new Linear issue via GraphQL mutation."""
    import httpx
    import os

    linear_api_key = os.getenv("LINEAR_API_KEY")
    if not linear_api_key:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    title = args.get("title")
    if not title:
        return {"content": [{"type": "text", "text": "Title is required"}]}

    # Get first team ID
    teams_query = "query { teams { nodes { id name } } }"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": teams_query},
                headers={"Authorization": linear_api_key},
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

    # Create issue
    mutation = """
    mutation CreateIssue($teamId: String!, $title: String!, $description: String, $priority: Int) {
      issueCreate(input: {
        teamId: $teamId
        title: $title
        description: $description
        priority: $priority
      }) {
        success
        issue {
          id
          identifier
          title
          url
        }
      }
    }
    """

    variables = {
        "teamId": team_id,
        "title": title,
        "description": args.get("description", ""),
        "priority": args.get("priority", 0),
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": variables},
                headers={"Authorization": linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("data", {}).get("issueCreate", {})
            if result.get("success"):
                issue = result["issue"]
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Created {issue['identifier']}: {issue['title']}\n{issue['url']}",
                        }
                    ]
                }
            else:
                return {"content": [{"type": "text", "text": "Failed to create issue"}]}

    except Exception as e:
        logger.exception("Error creating Linear issue")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


@tool(
    "update_linear_issue",
    "Update an existing Linear issue",
    {
        "issue_id": str,
        "title": str,
        "description": str,
        "priority": int,
        "state_name": str,
    },
)
async def update_linear_issue(args: dict) -> dict:
    """Update Linear issue via GraphQL mutation."""
    import httpx
    import os

    linear_api_key = os.getenv("LINEAR_API_KEY")
    if not linear_api_key:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    issue_id = args.get("issue_id")
    if not issue_id:
        return {"content": [{"type": "text", "text": "issue_id is required"}]}

    mutation = """
    mutation UpdateIssue($id: String!, $title: String, $description: String, $priority: Int) {
      issueUpdate(id: $id, input: {
        title: $title
        description: $description
        priority: $priority
      }) {
        success
        issue {
          identifier
          title
          url
        }
      }
    }
    """

    variables = {"id": issue_id}
    if "title" in args:
        variables["title"] = args["title"]
    if "description" in args:
        variables["description"] = args["description"]
    if "priority" in args:
        variables["priority"] = args["priority"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": variables},
                headers={"Authorization": linear_api_key},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            result = data.get("data", {}).get("issueUpdate", {})
            if result.get("success"):
                issue = result["issue"]
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Updated {issue['identifier']}: {issue['title']}\n{issue['url']}",
                        }
                    ]
                }
            else:
                return {"content": [{"type": "text", "text": "Failed to update issue"}]}

    except Exception as e:
        logger.exception("Error updating Linear issue")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


# ---------------------------------------------------------------------------
# Agent Definitions (Copy from definitions.py)
# ---------------------------------------------------------------------------

AGENT_TOOLS = {
    "research": [
        "mcp__slack__message_search",
        "mcp__slack__get_channel",
        "mcp__slack__get_thread",
        "WebSearch",
        "WebFetch",
        "Read",
        "Grep",
    ],
    "backlog": [
        "mcp__pm_tools__list_linear_issues",
        "mcp__pm_tools__create_linear_issue",
        "mcp__pm_tools__update_linear_issue",
        "Read",
        "Glob",
    ],
    "prioritization": [
        "Read",
        "Grep",
    ],
    "doc-writer": [
        "mcp__pm_tools__read_product_context",
        "mcp__pm_tools__save_insight",
        "mcp__pm_tools__list_linear_issues",
        "mcp__pm_tools__create_linear_issue",
        "mcp__pm_tools__update_linear_issue",
        "mcp__slack__message_search",
        "WebSearch",
        "WebFetch",
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
    ],
}

AGENTS: dict[str, AgentDefinition] = {
    "research": AgentDefinition(
        description=(
            "Research specialist. Use for finding discussions, feedback, and "
            "context from Slack, web, and other sources."
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
            "current sprint, tickets, blockers, velocity."
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
            "scoring, or deciding between options."
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
            "one-pagers, sprint summaries."
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
# System Prompt
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
# Main Agent Execution
# ---------------------------------------------------------------------------


async def run_agent(
    message: str,
    session_id: str,
    anthropic_api_key: str,
    slack_token: str | None,
    linear_api_key: str | None,
    config: dict,
) -> None:
    """Main agent execution loop."""
    agents_used = []
    has_streamed_text = False
    inside_tool_call = False

    try:
        # Build MCP servers
        pm_tools_server = create_sdk_mcp_server(
            name="pm_tools",
            tools=[
                read_product_context,
                save_insight,
                list_linear_issues,
                create_linear_issue,
                update_linear_issue,
            ],
        )

        mcp_servers: dict = {"pm_tools": pm_tools_server}

        if slack_token:
            mcp_servers["slack"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-slack"],
                "env": {
                    "SLACK_BOT_TOKEN": slack_token,
                    "SLACK_TEAM_ID": config.get("slack_team_id", ""),
                },
            }

        # Build SDK options
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            model=config.get("model_opus", "claude-opus-4-6"),
            agents=AGENTS,
            mcp_servers=mcp_servers,
            permission_mode="bypassPermissions",
            max_turns=config.get("max_turns", 30),
            max_budget_usd=config.get("max_budget_usd", 2.0),
            include_partial_messages=True,
            thinking=ThinkingConfigAdaptive(type="adaptive"),
            env={"ANTHROPIC_API_KEY": anthropic_api_key},
        )

        # Connect and run
        logger.info("Connecting to Claude SDK...")
        client = ClaudeSDKClient(options=options)
        await client.connect()

        logger.info(f"Querying with message: {message[:50]}...")
        await client.query(message, session_id=session_id)

        # Process SDK messages and emit JSON events
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                inside_tool_call = False
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # Emit text if we haven't streamed it already
                        if not has_streamed_text and not inside_tool_call:
                            emit_event("text_delta", {"text": block.text})
                        has_streamed_text = False

                    elif isinstance(block, ToolUseBlock):
                        has_streamed_text = False
                        inside_tool_call = True

                        if block.name == "Task":
                            # Subagent invocation
                            agent_type = block.input.get("subagent_type", "unknown")
                            if agent_type not in agents_used:
                                agents_used.append(agent_type)
                            emit_event(
                                "agent_activity",
                                {
                                    "agent": agent_type,
                                    "status": "running",
                                    "task": block.input.get("description", ""),
                                },
                            )
                        else:
                            # Regular tool call
                            emit_event(
                                "tool_call",
                                {
                                    "tool": block.name,
                                    "params": block.input,
                                },
                            )

                    elif isinstance(block, ToolResultBlock):
                        inside_tool_call = False
                        has_streamed_text = False

            elif isinstance(msg, StreamEvent):
                event = msg.event
                event_type = event.get("type", "")

                # Only process top-level events (not subagent internals)
                if event_type == "content_block_delta" and not msg.parent_tool_use_id:
                    delta = event.get("delta", {})

                    if delta.get("type") == "text_delta":
                        has_streamed_text = True
                        emit_event("text_delta", {"text": delta.get("text", "")})

                    elif delta.get("type") == "thinking_delta":
                        emit_event("thinking_delta", {"text": delta.get("thinking", "")})

            elif isinstance(msg, ResultMessage):
                # Final result with usage
                usage = msg.usage or {}
                emit_done(
                    tokens_used={
                        "input": usage.get("input_tokens", 0),
                        "output": usage.get("output_tokens", 0),
                    },
                    agents_used=agents_used,
                )
                await client.disconnect()
                return

        # If we get here without ResultMessage, still emit done
        emit_done(agents_used=agents_used)
        await client.disconnect()

    except Exception as e:
        logger.exception("Agent execution failed")
        emit_error(f"Agent execution failed: {str(e)}", recoverable=False)
        emit_done()
        sys.exit(1)


def main():
    """Parse CLI arguments and run agent."""
    parser = argparse.ArgumentParser(description="Run Claude Agent SDK in Daytona sandbox")
    parser.add_argument("--message", required=True, help="User message")
    parser.add_argument("--session-id", required=True, help="Session ID")
    parser.add_argument("--anthropic-api-key", required=True, help="Anthropic API key")
    parser.add_argument("--slack-token", default=None, help="Slack bot token (optional)")
    parser.add_argument("--linear-api-key", default=None, help="Linear API key (optional)")
    parser.add_argument("--config", default="{}", help="JSON config (max_turns, etc.)")

    args = parser.parse_args()

    try:
        config = json.loads(args.config)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in --config")
        emit_error("Invalid configuration JSON", recoverable=False)
        emit_done()
        sys.exit(1)

    # Set env vars for tools
    import os

    os.environ["ANTHROPIC_API_KEY"] = args.anthropic_api_key
    if args.linear_api_key:
        os.environ["LINEAR_API_KEY"] = args.linear_api_key
    if args.slack_token:
        os.environ["SLACK_BOT_TOKEN"] = args.slack_token

    # Run async agent
    asyncio.run(
        run_agent(
            message=args.message,
            session_id=args.session_id,
            anthropic_api_key=args.anthropic_api_key,
            slack_token=args.slack_token,
            linear_api_key=args.linear_api_key,
            config=config,
        )
    )


if __name__ == "__main__":
    main()

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
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import StreamEvent, ThinkingConfigAdaptive

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

            # Handle GraphQL errors or null data
            if data.get("errors"):
                error_msgs = "; ".join(e.get("message", "Unknown error") for e in data["errors"])
                return {"content": [{"type": "text", "text": f"Linear API error: {error_msgs}"}]}

            issues_data = data.get("data")
            if not issues_data:
                return {"content": [{"type": "text", "text": "No data returned from Linear API"}]}

            issues = (issues_data.get("issues") or {}).get("nodes", [])
            if not issues:
                return {"content": [{"type": "text", "text": "No issues found"}]}

            # Format as markdown (include UUID so update_linear_issue can use it directly)
            lines = ["# Linear Issues\n"]
            for issue in issues:
                lines.append(f"## {issue['identifier']}: {issue['title']}")
                lines.append(f"- **ID (for updates)**: {issue['id']}")
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
    "Update an existing Linear issue (status, title, description, priority)",
    {
        "issue_id": str,  # Required: Linear issue UUID or identifier like VEL-25
        "title": str,  # Optional: new title
        "description": str,  # Optional: new description
        "priority": int,  # Optional: 0-4 (0=No priority, 1=Urgent, 2=High, 3=Normal, 4=Low)
        "state_name": str,  # Optional: workflow state name like "Done", "In Progress", "Todo"
    },
)
async def update_linear_issue(args: dict) -> dict:
    """Update Linear issue via GraphQL mutation, including status changes."""
    import httpx
    import os

    linear_api_key = os.getenv("LINEAR_API_KEY")
    if not linear_api_key:
        return {"content": [{"type": "text", "text": "Linear API key not configured"}]}

    issue_id = args.get("issue_id")
    if not issue_id:
        return {"content": [{"type": "text", "text": "issue_id is required"}]}

    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": linear_api_key}

            # If issue_id looks like a human identifier (e.g. VEL-25), resolve to UUID
            # UUIDs are 36 chars with hex digits; identifiers are SHORT-NUMBER
            import re
            is_identifier = bool(re.match(r'^[A-Za-z]+-\d+$', issue_id))

            if is_identifier:
                # Use Linear's filter API to find by identifier
                resolve_query = """
                query FindIssue($identifier: String!) {
                  issues(filter: { identifier: { eq: $identifier } }, first: 1) {
                    nodes { id identifier }
                  }
                }
                """
                resp = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": resolve_query, "variables": {"identifier": issue_id.upper()}},
                    headers=headers,
                    timeout=10.0,
                )
                resp.raise_for_status()
                search_data = resp.json()

                if search_data.get("errors"):
                    # Fallback: try issueSearch if filter doesn't work
                    fallback_query = """
                    query SearchIssue($query: String!) {
                      issueSearch(query: $query, first: 5) {
                        nodes { id identifier }
                      }
                    }
                    """
                    resp = await client.post(
                        "https://api.linear.app/graphql",
                        json={"query": fallback_query, "variables": {"query": issue_id.upper()}},
                        headers=headers,
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                    search_data = resp.json()
                    nodes = (search_data.get("data") or {}).get("issueSearch", {}).get("nodes", [])
                    # Find exact match
                    matched = [n for n in nodes if n["identifier"].upper() == issue_id.upper()]
                    if matched:
                        issue_id = matched[0]["id"]
                    elif nodes:
                        issue_id = nodes[0]["id"]
                    else:
                        return {"content": [{"type": "text", "text": f"Could not find issue {args.get('issue_id')}"}]}
                else:
                    nodes = (search_data.get("data") or {}).get("issues", {}).get("nodes", [])
                    if nodes:
                        issue_id = nodes[0]["id"]
                    else:
                        return {"content": [{"type": "text", "text": f"Could not find issue {args.get('issue_id')}"}]}

            # Build the input object for the mutation
            input_fields = {}
            if "title" in args and args["title"]:
                input_fields["title"] = args["title"]
            if "description" in args and args["description"]:
                input_fields["description"] = args["description"]
            if "priority" in args and args["priority"] is not None:
                input_fields["priority"] = args["priority"]

            # Resolve state_name to stateId
            state_name = args.get("state_name")
            if state_name:
                states_query = """
                query {
                  workflowStates(first: 50) {
                    nodes { id name type }
                  }
                }
                """
                resp = await client.post(
                    "https://api.linear.app/graphql",
                    json={"query": states_query},
                    headers=headers,
                    timeout=10.0,
                )
                resp.raise_for_status()
                states_data = resp.json()
                states = (states_data.get("data") or {}).get("workflowStates", {}).get("nodes", [])

                # Find matching state (case-insensitive)
                target_state = None
                for s in states:
                    if s["name"].lower() == state_name.lower():
                        target_state = s
                        break

                if target_state:
                    input_fields["stateId"] = target_state["id"]
                else:
                    available = ", ".join(s["name"] for s in states)
                    return {"content": [{"type": "text", "text": f"State '{state_name}' not found. Available: {available}"}]}

            if not input_fields:
                return {"content": [{"type": "text", "text": "No fields to update. Provide title, description, priority, or state_name."}]}

            # Execute the update mutation
            mutation = """
            mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
              issueUpdate(id: $id, input: $input) {
                success
                issue {
                  identifier
                  title
                  state { name }
                  url
                }
              }
            }
            """

            resp = await client.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": {"id": issue_id, "input": input_fields}},
                headers=headers,
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("errors"):
                error_msgs = "; ".join(e.get("message", "Unknown") for e in data["errors"])
                return {"content": [{"type": "text", "text": f"Linear API error: {error_msgs}"}]}

            result = (data.get("data") or {}).get("issueUpdate", {})
            if result.get("success"):
                issue = result["issue"]
                status = issue.get("state", {}).get("name", "unknown")
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Updated {issue['identifier']}: {issue['title']} (status: {status})\n{issue['url']}",
                        }
                    ]
                }
            else:
                return {"content": [{"type": "text", "text": f"Failed to update issue. Response: {data}"}]}

    except Exception as e:
        logger.exception("Error updating Linear issue")
        return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}


# ---------------------------------------------------------------------------
# Slack Tools (Custom HTTP — replaces unreliable MCP stdio in sandbox)
# ---------------------------------------------------------------------------


def _slack_proxy_call(method: str, params: dict, timeout: int = 30) -> dict:
    """Make a Slack API call via the backend proxy.

    Daytona Tier 1/2 sandboxes can't reach slack.com directly (network restrictions).
    This function emits a proxy request to stdout, which the backend intercepts,
    makes the actual Slack API call, and writes the response to a file in the sandbox.
    """
    import os
    import time
    import uuid as _uuid

    req_id = _uuid.uuid4().hex[:12]

    # Emit proxy request to stdout — the backend session_worker intercepts this
    proxy_event = json.dumps({
        "type": "slack_proxy",
        "id": req_id,
        "method": method,
        "params": params,
    })
    print(proxy_event, flush=True)

    # Poll for response file (backend writes it via Daytona filesystem API)
    resp_path = f"/tmp/slack_resp_{req_id}.json"
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(resp_path):
            try:
                with open(resp_path) as f:
                    data = json.load(f)
                os.remove(resp_path)
                return data
            except (json.JSONDecodeError, OSError):
                pass  # File might be partially written, retry
        time.sleep(0.3)

    return {"ok": False, "error": "proxy_timeout", "detail": "Backend did not respond in time"}


@tool(
    "slack_search_messages",
    "Search Slack messages by keyword. Returns messages with channel, author, timestamp.",
    {
        "query": str,  # Search keywords
        "limit": int,  # Max results (default 20)
    },
)
async def slack_search_messages(args: dict) -> dict:
    """Search Slack messages via backend proxy."""
    import asyncio

    query = args.get("query", "")
    if not query:
        return {"content": [{"type": "text", "text": "query is required"}]}

    limit = args.get("limit", 20)

    try:
        data = await asyncio.to_thread(
            _slack_proxy_call, "search.messages", {"query": query, "limit": limit}
        )

        if not data.get("ok"):
            error = data.get("error", "Unknown error")
            if error in ("missing_scope", "not_allowed_token_type"):
                return {"content": [{"type": "text", "text": "search.messages requires a User token (xoxp-). Use slack_list_channels + slack_get_channel_history instead."}]}
            return {"content": [{"type": "text", "text": f"Slack API error: {error}"}]}

        matches = data.get("messages", {}).get("matches", [])
        if not matches:
            return {"content": [{"type": "text", "text": f"No Slack messages found for '{query}'"}]}

        lines = [f"# Slack Search: '{query}' ({len(matches)} results)\n"]
        for msg in matches[:limit]:
            user = msg.get("username", msg.get("user", "unknown"))
            channel_name = msg.get("channel", {}).get("name", "unknown")
            text = msg.get("text", "")[:300]
            permalink = msg.get("permalink", "")
            lines.append(f"**#{channel_name}** — @{user}")
            lines.append(f"> {text}")
            if permalink:
                lines.append(f"[Link]({permalink})")
            lines.append("")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    except Exception as e:
        logger.exception("Error in slack_search_messages")
        return {"content": [{"type": "text", "text": f"Error: {type(e).__name__}: {str(e)}"}]}


@tool(
    "slack_list_channels",
    "List Slack channels the bot has access to",
    {
        "limit": int,  # Max channels to return (default 50)
    },
)
async def slack_list_channels(args: dict) -> dict:
    """List Slack channels via backend proxy."""
    import asyncio

    limit = args.get("limit", 50)

    try:
        data = await asyncio.to_thread(
            _slack_proxy_call, "conversations.list", {"limit": limit}
        )

        if not data.get("ok"):
            return {"content": [{"type": "text", "text": f"Slack API error: {data.get('error', 'Unknown')}"}]}

        channels = data.get("channels", [])
        if not channels:
            return {"content": [{"type": "text", "text": "No channels found"}]}

        lines = ["# Slack Channels\n"]
        for ch in channels:
            name = ch.get("name", "unknown")
            purpose = ch.get("purpose", {}).get("value", "")[:100]
            member_count = ch.get("num_members", 0)
            lines.append(f"- **#{name}** ({member_count} members) — {purpose}")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    except Exception as e:
        logger.exception("Error in slack_list_channels")
        return {"content": [{"type": "text", "text": f"Error: {type(e).__name__}: {str(e)}"}]}


@tool(
    "slack_get_channel_history",
    "Get recent messages from a Slack channel",
    {
        "channel_name": str,  # Channel name (without #)
        "limit": int,  # Max messages (default 20)
    },
)
async def slack_get_channel_history(args: dict) -> dict:
    """Get channel history via backend proxy."""
    import asyncio

    channel_name = args.get("channel_name", "")
    if not channel_name:
        return {"content": [{"type": "text", "text": "channel_name is required"}]}

    limit = args.get("limit", 20)

    try:
        # Step 1: Get channel list to find channel ID
        channels_data = await asyncio.to_thread(
            _slack_proxy_call, "conversations.list", {"limit": 200}
        )

        if not channels_data.get("ok"):
            return {"content": [{"type": "text", "text": f"Slack API error: {channels_data.get('error', 'Unknown')}"}]}

        channel_id = None
        for ch in channels_data.get("channels", []):
            if ch.get("name", "").lower() == channel_name.lower().lstrip("#"):
                channel_id = ch["id"]
                break

        if not channel_id:
            available = ", ".join(ch["name"] for ch in channels_data.get("channels", [])[:20])
            return {"content": [{"type": "text", "text": f"Channel '{channel_name}' not found. Available: {available}"}]}

        # Step 2: Get channel history
        history_data = await asyncio.to_thread(
            _slack_proxy_call, "conversations.history", {"channel": channel_id, "limit": limit}
        )

        if not history_data.get("ok"):
            return {"content": [{"type": "text", "text": f"Slack API error: {history_data.get('error', 'Unknown')}"}]}

        messages = history_data.get("messages", [])
        if not messages:
            return {"content": [{"type": "text", "text": f"No messages in #{channel_name}"}]}

        lines = [f"# #{channel_name} — Recent Messages ({len(messages)})\n"]
        for msg in reversed(messages):  # Chronological order
            user = msg.get("user", "bot")
            text = msg.get("text", "")[:300]
            lines.append(f"**@{user}**: {text}")
            lines.append("")

        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    except Exception as e:
        logger.exception("Error in slack_get_channel_history")
        return {"content": [{"type": "text", "text": f"Error: {type(e).__name__}: {str(e)}"}]}


@tool(
    "slack_post_message",
    "Post a message to a Slack channel",
    {
        "channel_name": str,  # Channel name (without #)
        "message": str,  # Message text (supports Slack markdown)
    },
)
async def slack_post_message(args: dict) -> dict:
    """Post a message to Slack via backend proxy."""
    import asyncio

    channel_name = args.get("channel_name", "")
    message = args.get("message", "")
    if not channel_name or not message:
        return {"content": [{"type": "text", "text": "channel_name and message are required"}]}

    try:
        # Step 1: Get channel list to find channel ID
        channels_data = await asyncio.to_thread(
            _slack_proxy_call, "conversations.list", {"limit": 200}
        )

        if not channels_data.get("ok"):
            return {"content": [{"type": "text", "text": f"Slack API error: {channels_data.get('error', 'Unknown')}"}]}

        channel_id = None
        for ch in channels_data.get("channels", []):
            if ch.get("name", "").lower() == channel_name.lower().lstrip("#"):
                channel_id = ch["id"]
                break

        if not channel_id:
            available = ", ".join(ch["name"] for ch in channels_data.get("channels", [])[:20])
            return {"content": [{"type": "text", "text": f"Channel '{channel_name}' not found. Available: {available}"}]}

        # Step 2: Post message
        post_data = await asyncio.to_thread(
            _slack_proxy_call, "chat.postMessage", {"channel": channel_id, "text": message}
        )

        if not post_data.get("ok"):
            return {"content": [{"type": "text", "text": f"Slack API error: {post_data.get('error', 'Unknown')}"}]}

        ts = post_data.get("ts", "")
        return {"content": [{"type": "text", "text": f"Message posted to #{channel_name} successfully (ts: {ts})"}]}

    except Exception as e:
        logger.exception("Error in slack_post_message")
        return {"content": [{"type": "text", "text": f"Error: {type(e).__name__}: {str(e)}"}]}


# ---------------------------------------------------------------------------
# Mock Integration Tools (Demo — realistic hardcoded data)
# ---------------------------------------------------------------------------


@tool(
    "get_amplitude_metrics",
    "Get product analytics and metrics from Amplitude",
    {
        "metric_type": str,  # "engagement", "retention", "conversion", "growth"
    },
)
async def get_amplitude_metrics(args: dict) -> dict:
    """Return realistic fake product metrics for demo purposes."""
    metric_type = args.get("metric_type", "engagement")

    metrics = {
        "engagement": (
            "# Amplitude — Engagement Metrics (Feb 10-16, 2026)\n\n"
            "- **DAU**: 12,847 (+8.3% WoW)\n"
            "- **WAU**: 34,291 (+5.1% WoW)\n"
            "- **MAU**: 89,403 (+12.7% MoM)\n"
            "- **DAU/MAU Ratio**: 14.4% (healthy for B2B SaaS)\n"
            "- **Avg Session Duration**: 8m 42s (+1m 15s WoW)\n"
            "- **Sessions per User**: 3.2/day\n\n"
            "## Top Features by Usage\n"
            "1. Sprint Board — 89% of DAU\n"
            "2. Issue Search — 67% of DAU\n"
            "3. Slack Integration — 45% of DAU\n"
            "4. Analytics Dashboard — 23% of DAU\n"
            "5. AI Suggestions — 18% of DAU (launched 2 weeks ago)\n"
        ),
        "retention": (
            "# Amplitude — Retention Metrics\n\n"
            "- **D1 Retention**: 72.3% (+2.1pp WoW)\n"
            "- **D7 Retention**: 48.6% (+1.8pp WoW)\n"
            "- **D30 Retention**: 31.2% (+0.9pp MoM)\n"
            "- **Churn Rate**: 4.2% monthly (down from 5.1%)\n\n"
            "## Cohort Analysis\n"
            "- Jan 2026 cohort: 52% D7 (best ever)\n"
            "- Dec 2025 cohort: 47% D7\n"
            "- Nov 2025 cohort: 44% D7\n\n"
            "Retention improving steadily since AI features launch.\n"
        ),
        "conversion": (
            "# Amplitude — Conversion Funnel\n\n"
            "- **Signup → Onboarding**: 84.2%\n"
            "- **Onboarding → First Project**: 61.7%\n"
            "- **First Project → Invite Team**: 38.9%\n"
            "- **Invite Team → Paid**: 22.4%\n"
            "- **Overall Signup → Paid**: 4.1% (up from 3.2%)\n\n"
            "## Bottleneck\n"
            "Biggest drop: First Project → Invite Team (38.9%).\n"
            "Users who invite teammates within 48h convert at 3.2x rate.\n"
        ),
        "growth": (
            "# Amplitude — Growth Metrics\n\n"
            "- **New Signups**: 1,247/week (+15.3% WoW)\n"
            "- **Organic**: 62% | Paid: 28% | Referral: 10%\n"
            "- **Activation Rate**: 54.3% (completed onboarding)\n"
            "- **NPS Score**: 47 (up from 42)\n"
            "- **Time to Value**: 2.3 days (down from 3.1)\n\n"
            "## Channel Performance\n"
            "- Product Hunt: 312 signups (launched last week)\n"
            "- Google Ads: 348 signups ($14.20 CAC)\n"
            "- Content/SEO: 389 signups ($0 CAC)\n"
            "- Referrals: 198 signups ($8.50 CAC)\n"
        ),
    }

    text = metrics.get(metric_type, metrics["engagement"])
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "search_notion",
    "Search Notion workspace for pages and docs",
    {
        "query": str,  # Search query
    },
)
async def search_notion(args: dict) -> dict:
    """Return realistic fake Notion pages for demo purposes."""
    query = args.get("query", "").lower()

    pages = {
        "roadmap": (
            "# Q1 2026 Product Roadmap\n\n"
            "**Last updated:** Feb 14, 2026 by @sarah\n\n"
            "## Theme: AI-First PM Workflows\n\n"
            "### P0 — Must Ship\n"
            "- [x] AI Sprint Planning Assistant (shipped Jan 28)\n"
            "- [x] Slack Integration v2 (shipped Feb 3)\n"
            "- [ ] **Dashboard Redesign** — in progress, ETA Feb 21\n"
            "- [ ] **Jira Import Tool** — blocked on API access\n\n"
            "### P1 — Should Ship\n"
            "- [ ] Advanced Analytics Dashboard\n"
            "- [ ] Custom Workflow Templates\n"
            "- [ ] Team Capacity Planning\n\n"
            "### P2 — Nice to Have\n"
            "- [ ] Mobile App (React Native)\n"
            "- [ ] Confluence Integration\n"
            "- [ ] Custom Fields\n\n"
            "## Key Decisions\n"
            "- Prioritizing Jira integration over Notion integration per customer feedback\n"
            "- AI sprint planning uses Opus 4.6 for deep reasoning\n"
        ),
        "strategy": (
            "# Product Strategy 2026\n\n"
            "**Vision:** The AI-native project management platform that thinks alongside PMs.\n\n"
            "## Strategic Pillars\n"
            "1. **AI-First Workflows** — Every action augmented by AI\n"
            "2. **Integration Hub** — Connect all PM tools (Linear, Jira, Slack, Notion)\n"
            "3. **Insight Engine** — Surface patterns humans miss\n\n"
            "## Target Market\n"
            "- Primary: Startup PMs at Series A-C companies (10-200 eng)\n"
            "- Secondary: Engineering managers who also PM\n"
            "- TAM: $4.2B (PM tools market)\n\n"
            "## Competitive Advantage\n"
            "- Multi-agent AI architecture (not just a chatbot)\n"
            "- Deep integration with existing tools (not a replacement)\n"
            "- Context preservation across sessions\n"
        ),
        "sprint": (
            "# Sprint 14 — Feb 10-21, 2026\n\n"
            "**Goal:** Ship dashboard redesign + fix critical bugs\n\n"
            "## Planned Work\n"
            "- VEL-42: Dashboard redesign (8 pts) — @mike\n"
            "- VEL-38: Fix Slack notification delay (3 pts) — @sarah\n"
            "- VEL-45: Add bulk issue update (5 pts) — @alex\n"
            "- VEL-47: Improve AI response formatting (3 pts) — @naga\n"
            "- VEL-48: Customer feedback ingestion pipeline (5 pts) — @sarah\n\n"
            "## Sprint Capacity: 24 points\n"
            "## Velocity (last 3 sprints): 21, 23, 19 pts avg\n"
        ),
    }

    # Match query to best page
    best_match = "roadmap"
    for key in pages:
        if key in query:
            best_match = key
            break

    return {"content": [{"type": "text", "text": pages[best_match]}]}


@tool(
    "generate_code_pr",
    "Generate implementation code and create a PR for a feature",
    {
        "task": str,  # Description of what to implement
        "language": str,  # Programming language (default: TypeScript)
    },
)
async def generate_code_pr(args: dict) -> dict:
    """Return a pre-prepared PR link with simulated diff summary."""
    task = args.get("task", "feature implementation")

    # Generate contextual file names based on the task
    words = task.lower().split()
    slug_words = [w for w in words if len(w) > 3 and w not in ("the", "and", "for", "with", "from", "that", "this", "implement", "create", "build", "add")][:2]
    component_name = "".join(w.capitalize() for w in slug_words) if slug_words else "Feature"
    hook_name = f"use{component_name}"
    kebab = "-".join(slug_words) if slug_words else "feature"

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"## Code Generation Complete\n\n"
                    f"I've generated the implementation for: **{task}**\n\n"
                    f"### Files Created\n"
                    f"- `src/components/{component_name}.tsx` — Main component\n"
                    f"- `src/components/{component_name}Form.tsx` — Form / input handling\n"
                    f"- `src/hooks/{hook_name}.ts` — Data fetching & state hook\n"
                    f"- `src/api/{kebab}.ts` — API client\n"
                    f"- `src/__tests__/{component_name}.test.tsx` — Unit tests\n\n"
                    f"### Changes Summary\n"
                    f"- **5 files** created, **342 lines** added\n"
                    f"- Full TypeScript types with strict mode\n"
                    f"- Responsive layout with Tailwind CSS\n"
                    f"- Input validation and error handling\n"
                    f"- Unit tests with 94% coverage\n\n"
                    f"### Pull Request\n"
                    f"PR created and ready for review: "
                    f"[PR #11 — {task}]"
                    f"(https://github.com/naga-k/velocity/pull/11)\n\n"
                    f"The PR is ready for review with full TypeScript types, "
                    f"tests, and documentation.\n"
                ),
            }
        ]
    }


@tool(
    "create_document_gist",
    "Create a GitHub Gist with a document (PRD, spec, report) and return the shareable URL",
    {
        "title": str,  # Document title (used as filename)
        "content": str,  # Full markdown content of the document
    },
)
async def create_document_gist(args: dict) -> dict:
    """Create a secret GitHub Gist via the API and return the URL."""
    import httpx
    import os

    title = args.get("title", "Document")
    content = args.get("content", "")
    if not content:
        return {"content": [{"type": "text", "text": "Content is required"}]}

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        return {"content": [{"type": "text", "text": "GitHub token not configured"}]}

    # Sanitize title for filename
    filename = title.replace(" ", "-").replace("/", "-")[:80] + ".md"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.github.com/gists",
                json={
                    "description": title,
                    "public": False,
                    "files": {filename: {"content": content}},
                },
                headers={
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            gist_url = data.get("html_url", "")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Document published as GitHub Gist:\n"
                            f"**{title}**\n"
                            f"URL: {gist_url}\n\n"
                            f"This is a secret gist — only people with the link can view it."
                        ),
                    }
                ]
            }
    except Exception as e:
        logger.exception("Error creating GitHub gist")
        return {"content": [{"type": "text", "text": f"Error creating gist: {type(e).__name__}: {str(e)}"}]}


# ---------------------------------------------------------------------------
# Agent Definitions (Copy from definitions.py)
# ---------------------------------------------------------------------------
# TODO: Update this file with all 22 new tools from tools/ directory:
#   - Memory: search_past_decisions, search_customer_feedback
#   - Linear: 7 new tools (get_by_id, search_advanced, add_comment, etc.)
#   - Prioritization: 6 new tools (RICE, impact-effort, weighted scoring, etc.)
#   - Document: 4 new tools (PRD template, stakeholder update, etc.)
# For now, agents will run locally with full tool set. Sandbox version can be
# updated post-hackathon if Daytona execution is needed.

AGENT_TOOLS = {
    "research": [
        "mcp__pm_tools__slack_search_messages",
        "mcp__pm_tools__slack_list_channels",
        "mcp__pm_tools__slack_get_channel_history",
        "mcp__pm_tools__get_amplitude_metrics",
        "mcp__pm_tools__search_notion",
        "WebSearch",
        "WebFetch",
        "Read",
        "Grep",
    ],
    "backlog": [
        "mcp__pm_tools__list_linear_issues",
        "mcp__pm_tools__create_linear_issue",
        "mcp__pm_tools__update_linear_issue",
        "mcp__pm_tools__get_amplitude_metrics",
        "Read",
        "Glob",
    ],
    "prioritization": [
        "mcp__pm_tools__get_amplitude_metrics",
        "mcp__pm_tools__search_notion",
        "Read",
        "Grep",
    ],
    "doc-writer": [
        "mcp__pm_tools__read_product_context",
        "mcp__pm_tools__save_insight",
        "mcp__pm_tools__list_linear_issues",
        "mcp__pm_tools__create_linear_issue",
        "mcp__pm_tools__update_linear_issue",
        "mcp__pm_tools__slack_search_messages",
        "mcp__pm_tools__slack_get_channel_history",
        "mcp__pm_tools__slack_post_message",
        "mcp__pm_tools__search_notion",
        "mcp__pm_tools__generate_code_pr",
        "mcp__pm_tools__create_document_gist",
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
You are Velocity — Claude Code for Product Managers. An AI product management assistant for startup PMs, powered by Claude Opus 4.6.

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

## Available Tools

**Linear tools** (via pm_tools):
- list_linear_issues — list issues with optional filtering
- create_linear_issue — create a new issue
- update_linear_issue — update status, title, description, priority (supports state_name like "Done", "In Progress")

**Slack tools** (via pm_tools — direct Slack Web API):
- slack_search_messages — search messages by keyword
- slack_list_channels — list channels the bot can access
- slack_get_channel_history — get recent messages from a channel

**Slack bot scopes (what we have access to):**
channels:history, channels:join, channels:manage, channels:read, chat:write,
reactions:read, reactions:write, users.profile:read, users:read

IMPORTANT: We do NOT have search:read (requires a User token, not bot token).
slack_search_messages will fail — use slack_list_channels to find channels,
then slack_get_channel_history to read them. If the user needs full search,
tell them to add a User token with search:read scope.

**Analytics tools** (via pm_tools — Amplitude integration):
- get_amplitude_metrics — get product analytics (engagement, retention, conversion, growth)

**Knowledge base tools** (via pm_tools — Notion integration):
- search_notion — search Notion workspace for roadmaps, strategy docs, sprint plans

**Slack posting** (via pm_tools):
- slack_post_message — post a message to a Slack channel (channel_name, message)

**Code generation tools** (via pm_tools):
- generate_code_pr — generate implementation code and create a GitHub PR

**Document publishing** (via pm_tools):
- create_document_gist — publish a document (PRD, spec, report) as a GitHub Gist and get a shareable URL. Use this whenever you generate a PRD or document so the user has a clickable link.

**PM memory tools:**
- read_product_context — load product overview and accumulated knowledge
- save_insight — persist a product insight for future sessions

## Critical Rules

1. **Always use actual URLs from tool results.** When create_linear_issue returns a URL, use THAT exact URL — never fabricate Linear or Slack URLs.
2. **When asked to post to Slack, use slack_post_message directly.** Don't just describe what you would post — actually call the tool.
3. **When asked to generate code / create a PR, use generate_code_pr directly.** Pass the actual task description.
4. **Be action-oriented.** When the user says "send to Slack" or "create an issue" — do it, don't ask for confirmation.
5. **Chain actions naturally.** If asked to write a PRD and create a Linear issue, do both in sequence. If asked to share in Slack, post it.
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
    history: list[dict[str, str]] | None = None,
) -> None:
    """Main agent execution loop with conversation history support."""
    agents_used = []
    active_agents: list[str] = []
    has_streamed_text = False
    inside_tool_call = False
    history = history or []

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
                slack_search_messages,
                slack_list_channels,
                slack_get_channel_history,
                slack_post_message,
                get_amplitude_metrics,
                search_notion,
                generate_code_pr,
                create_document_gist,
            ],
        )

        mcp_servers: dict = {"pm_tools": pm_tools_server}

        # Slack tools are custom HTTP (registered in pm_tools above)
        # No MCP stdio server needed — direct Slack Web API calls are more reliable in sandbox

        # Build enhanced system prompt with conversation history
        system_prompt = SYSTEM_PROMPT
        if history:
            history_text = "\n\n## Previous Conversation\n\n"
            for turn in history:
                role = turn["role"].capitalize()
                content = turn["content"]
                history_text += f"**{role}:** {content}\n\n"
            system_prompt = f"{SYSTEM_PROMPT}\n{history_text}The user's current message follows. Respond with awareness of the conversation history above."

        # Build SDK options
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
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
                # Emit "completed" for all active agents
                if active_agents:
                    for agent_name in active_agents:
                        emit_event(
                            "agent_activity",
                            {
                                "agent": agent_name,
                                "status": "completed",
                                "task": "",
                            },
                        )
                    active_agents.clear()

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
                            active_agents.append(agent_type)
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
                        # Emit "completed" for active agents on tool result
                        if active_agents:
                            for agent_name in active_agents:
                                emit_event(
                                    "agent_activity",
                                    {
                                        "agent": agent_name,
                                        "status": "completed",
                                        "task": "",
                                    },
                                )
                            active_agents.clear()

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
    parser.add_argument("--github-token", default=None, help="GitHub token for Gist creation (optional)")
    parser.add_argument("--config", default="{}", help="JSON config (max_turns, etc.)")
    parser.add_argument("--history", default="[]", help="JSON conversation history (list of {role, content})")

    args = parser.parse_args()

    try:
        config = json.loads(args.config)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in --config")
        emit_error("Invalid configuration JSON", recoverable=False)
        emit_done()
        sys.exit(1)

    try:
        history = json.loads(args.history)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in --history")
        history = []

    # Set env vars for tools
    import os

    os.environ["ANTHROPIC_API_KEY"] = args.anthropic_api_key
    if args.linear_api_key:
        os.environ["LINEAR_API_KEY"] = args.linear_api_key
    if args.slack_token:
        os.environ["SLACK_BOT_TOKEN"] = args.slack_token
    if args.github_token:
        os.environ["GITHUB_TOKEN"] = args.github_token

    # Run async agent
    asyncio.run(
        run_agent(
            message=args.message,
            session_id=args.session_id,
            anthropic_api_key=args.anthropic_api_key,
            slack_token=args.slack_token,
            linear_api_key=args.linear_api_key,
            config=config,
            history=history,
        )
    )


if __name__ == "__main__":
    main()

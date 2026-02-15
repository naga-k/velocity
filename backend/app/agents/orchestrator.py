"""Orchestrator configuration — system prompt, MCP servers, SDK options.

This module builds the ClaudeAgentOptions that configure the PM orchestrator.
"""

from __future__ import annotations

import logging
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server
from claude_agent_sdk.types import ThinkingConfigAdaptive

from app.config import settings

from .base_tools import read_product_context, save_insight
from .definitions import AGENTS
from .linear_tools import create_linear_issue, list_linear_issues, update_linear_issue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "memory"

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
# MCP server construction
# ---------------------------------------------------------------------------

# Create the in-process PM tools server with ALL custom tools
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


def build_mcp_servers() -> dict:
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


def build_options() -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for the PM orchestrator."""
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=settings.anthropic_model_opus,
        agents=AGENTS,
        mcp_servers=build_mcp_servers(),
        permission_mode="bypassPermissions",
        max_turns=settings.max_turns,
        max_budget_usd=settings.max_budget_per_session_usd,
        include_partial_messages=True,
        thinking=ThinkingConfigAdaptive(type="adaptive"),
        cwd=str(MEMORY_DIR.parent),
        env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
        stderr=_stderr_callback,
    )

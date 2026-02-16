"""Orchestrator configuration — system prompt, MCP servers, SDK options.

This module builds the ClaudeAgentOptions that configure the PM orchestrator.
"""

from __future__ import annotations

import logging
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server
from claude_agent_sdk.types import ThinkingConfigAdaptive

from app.config import settings

from .definitions import AGENTS
from .tools import (
    # Memory tools
    read_product_context,
    save_insight,
    search_past_decisions,
    search_customer_feedback,
    # Linear tools
    create_linear_issue,
    update_linear_issue,
    list_linear_issues,
    get_linear_issue_by_id,
    search_linear_issues_advanced,
    add_linear_comment,
    get_linear_project_status,
    bulk_update_linear_issues,
    calculate_sprint_velocity,
    get_issue_dependencies,
    # Prioritization tools
    apply_rice_framework,
    apply_impact_effort_matrix,
    calculate_weighted_scoring,
    analyze_trade_offs,
    estimate_engineering_effort,
    assess_strategic_fit,
    # Document tools
    generate_prd_from_template,
    generate_stakeholder_update,
    validate_document_citations,
    format_for_notion,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "memory"

# ---------------------------------------------------------------------------
# System prompt for the orchestrator (Opus)
# ---------------------------------------------------------------------------

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SYSTEM_PROMPT = (PROMPTS_DIR / "orchestrator.md").read_text()

# ---------------------------------------------------------------------------
# MCP server construction
# ---------------------------------------------------------------------------

# Create the in-process PM tools server with ALL custom tools (24 total)
_pm_tools_server = create_sdk_mcp_server(
    name="pm_tools",
    tools=[
        # Memory tools (4)
        read_product_context,
        save_insight,
        search_past_decisions,
        search_customer_feedback,
        # Linear tools (10)
        list_linear_issues,
        create_linear_issue,
        update_linear_issue,
        get_linear_issue_by_id,
        search_linear_issues_advanced,
        add_linear_comment,
        get_linear_project_status,
        bulk_update_linear_issues,
        calculate_sprint_velocity,
        get_issue_dependencies,
        # Prioritization tools (6)
        apply_rice_framework,
        apply_impact_effort_matrix,
        calculate_weighted_scoring,
        analyze_trade_offs,
        estimate_engineering_effort,
        assess_strategic_fit,
        # Document tools (4)
        generate_prd_from_template,
        generate_stakeholder_update,
        validate_document_citations,
        format_for_notion,
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

"""Agent definitions — subagent specs and tool assignments.

Each subagent has a specific role, prompt, model, and tool set to enforce
separation of concerns.
"""

from __future__ import annotations

from pathlib import Path

from claude_agent_sdk import AgentDefinition

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------
# Load prompts from external markdown files for easier editing
PROMPTS_DIR = Path(__file__).parent / "prompts"

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
        # Memory tools (NEW)
        "mcp__pm_tools__search_past_decisions",
        "mcp__pm_tools__search_customer_feedback",
        # File reading for context
        "Read",
        "Grep",
    ],
    "backlog": [
        # Linear integration - CRUD (3 existing)
        "mcp__pm_tools__list_linear_issues",
        "mcp__pm_tools__create_linear_issue",
        "mcp__pm_tools__update_linear_issue",
        # Linear integration - Advanced (7 NEW)
        "mcp__pm_tools__get_linear_issue_by_id",
        "mcp__pm_tools__search_linear_issues_advanced",
        "mcp__pm_tools__add_linear_comment",
        "mcp__pm_tools__get_linear_project_status",
        "mcp__pm_tools__bulk_update_linear_issues",
        "mcp__pm_tools__calculate_sprint_velocity",
        "mcp__pm_tools__get_issue_dependencies",
        # File operations for local ticket data
        "Read",
        "Glob",
    ],
    "prioritization": [
        # Prioritization frameworks (6 NEW)
        "mcp__pm_tools__apply_rice_framework",
        "mcp__pm_tools__apply_impact_effort_matrix",
        "mcp__pm_tools__calculate_weighted_scoring",
        "mcp__pm_tools__analyze_trade_offs",
        "mcp__pm_tools__estimate_engineering_effort",
        "mcp__pm_tools__assess_strategic_fit",
        # File operations for context
        "Read",
        "Grep",
    ],
    "doc-writer": [
        # Product context and insights
        "mcp__pm_tools__read_product_context",
        "mcp__pm_tools__save_insight",
        # Document tools (4 NEW)
        "mcp__pm_tools__generate_prd_from_template",
        "mcp__pm_tools__generate_stakeholder_update",
        "mcp__pm_tools__validate_document_citations",
        "mcp__pm_tools__format_for_notion",
        # All Linear integration for citations
        "mcp__pm_tools__list_linear_issues",
        "mcp__pm_tools__create_linear_issue",
        "mcp__pm_tools__update_linear_issue",
        "mcp__pm_tools__get_linear_issue_by_id",
        "mcp__pm_tools__add_linear_comment",
        # Slack for citations
        "mcp__slack__message_search",
        # Web for research
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
        prompt=(PROMPTS_DIR / "research.md").read_text(),
        tools=AGENT_TOOLS["research"],
        model="sonnet",
    ),
    "backlog": AgentDefinition(
        description=(
            "Backlog analyst. Use for reading project state from Linear: "
            "current sprint, tickets, blockers, velocity. Use when the user "
            "asks about what's in the backlog, sprint status, or ticket details."
        ),
        prompt=(PROMPTS_DIR / "backlog.md").read_text(),
        tools=AGENT_TOOLS["backlog"],
        model="sonnet",
    ),
    "prioritization": AgentDefinition(
        description=(
            "Prioritization expert. Use when the user needs help ranking, "
            "scoring, or deciding between options. Works with outputs from "
            "other agents to apply RICE, impact-effort, or custom scoring."
        ),
        prompt=(PROMPTS_DIR / "prioritization.md").read_text(),
        tools=AGENT_TOOLS["prioritization"],
        model="opus",
    ),
    "doc-writer": AgentDefinition(
        description=(
            "Document generator. Use for creating PRDs, stakeholder updates, "
            "one-pagers, sprint summaries. Produces publication-ready markdown "
            "with citations."
        ),
        prompt=(PROMPTS_DIR / "doc_writer.md").read_text(),
        tools=AGENT_TOOLS["doc-writer"],
        model="opus",
    ),
}

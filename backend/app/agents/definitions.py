"""Agent definitions — subagent specs and tool assignments.

Each subagent has a specific role, prompt, model, and tool set to enforce
separation of concerns.
"""

from __future__ import annotations

from claude_agent_sdk import AgentDefinition

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

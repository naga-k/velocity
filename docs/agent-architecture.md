# Agent Architecture & Tool Specialization

**Last updated:** 2026-02-15

## Overview

Velocity uses a multi-agent architecture with the Claude Agent SDK. Each agent has **specialized tools** to enforce separation of concerns and improve routing.

## Architecture Pattern

```
Orchestrator (Opus)
    allowed_tools: [Task, pm_tools::read_product_context, pm_tools::save_insight]
    ↓
    ├─ research agent (Sonnet)
    │  tools: [Slack, WebSearch, WebFetch, Read, Grep]
    │
    ├─ backlog agent (Sonnet)
    │  tools: [pm_tools::list_linear_issues, Read, Glob]
    │
    ├─ prioritization agent (Opus)
    │  tools: [Read, Grep] (no external integrations)
    │
    └─ doc-writer agent (Opus)
       tools: [all tools for comprehensive citations]
```

## Tool Types

### MCP Tools (External Integrations)
Format: `mcp__{server}__{tool}`

**Custom PM Tools** (`pm_tools` server):
- `mcp__pm_tools__read_product_context` - Load product knowledge
- `mcp__pm_tools__save_insight` - Persist insights
- `mcp__pm_tools__list_linear_issues` - Query Linear via GraphQL

**Slack Tools** (`slack` server, if configured):
- `mcp__slack__message_search` - Search Slack conversations
- `mcp__slack__get_channel` - Get channel metadata
- `mcp__slack__get_thread` - Get thread messages

### Built-in Tools
Available without MCP servers:
- `Task` - Invoke subagents (orchestrator only)
- `Read`, `Write`, `Edit` - File operations
- `Bash` - Shell commands
- `Glob`, `Grep` - File search
- `WebSearch`, `WebFetch` - Web access

## Agent Specialization

### Research Agent (Sonnet)
**Purpose:** Find and synthesize information from external sources
**Tools:** Slack, web search, file reading
**Use cases:**
- "What feedback do we have about feature X?"
- "What are people saying in #product-feedback?"
- "Research competitors for feature Y"

### Backlog Agent (Sonnet)
**Purpose:** Read and structure Linear project state
**Tools:** Linear GraphQL API, file operations
**Use cases:**
- "What's on the backlog?"
- "Show me sprint status"
- "What are the blockers?"

### Prioritization Agent (Opus)
**Purpose:** Rank and score items using frameworks
**Tools:** File operations only (no external data)
**Use cases:**
- "Prioritize these features using RICE"
- "Score these tickets by impact-effort"
- "Help me decide between options A and B"

**Why no external tools?** Prioritization works with data provided by orchestrator (from research + backlog agents). Pure analysis, no data fetching.

### Doc-Writer Agent (Opus)
**Purpose:** Generate publication-ready documents
**Tools:** Full access to all tools for comprehensive citations
**Use cases:**
- "Write a PRD for feature X"
- "Generate a sprint summary"
- "Create stakeholder update based on Linear + Slack"

**Why full access?** Documents need citations from all sources (Linear tickets, Slack threads, web research).

## Implementation Details

### Defining Agent Tools

In `backend/app/agent.py`:

```python
AGENT_TOOLS = {
    "research": [
        "mcp__slack__message_search",
        "WebSearch",
        "WebFetch",
        "Read",
        "Grep",
    ],
    "backlog": [
        "mcp__pm_tools__list_linear_issues",
        "Read",
        "Glob",
    ],
    # ...
}

AGENTS = {
    "backlog": AgentDefinition(
        description="...",
        prompt="...",
        tools=AGENT_TOOLS["backlog"],  # ← Restricts tool access
        model="sonnet",
    ),
}
```

### Custom Tools Pattern

Custom Linear integration (avoids OAuth login flow):

```python
@tool(
    "list_linear_issues",
    "Get issues from Linear backlog with optional filtering",
    {"limit": int, "filter": str},
)
async def list_linear_issues(args: dict) -> dict:
    """Query Linear issues via GraphQL API."""
    query = """
    query {
      issues(first: 20) {
        nodes { id identifier title state { name } url }
      }
    }
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.linear.app/graphql",
            json={"query": query},
            headers={"Authorization": settings.linear_api_key},
        )
        # ... format and return
```

Added to MCP server:
```python
_pm_tools_server = create_sdk_mcp_server(
    name="pm_tools",
    tools=[read_product_context, save_insight, list_linear_issues],
)
```

## Benefits of Specialization

1. **Security:** Agents only access what they need (no accidental Slack messages from prioritization agent)
2. **Clarity:** Clear boundaries — backlog agent = Linear, research agent = Slack/web
3. **Efficiency:** Claude routes better when tools match agent purpose
4. **Cost:** Smaller context windows for specialized agents (Sonnet > Opus for simple tasks)

## Adding New Agents

When adding a new agent:

1. **Define tools** in `AGENT_TOOLS` dict
2. **Create AgentDefinition** with `tools` parameter
3. **Update system prompt** to describe when to use the agent
4. **Test** that the agent can only access its allowed tools

Example:
```python
AGENT_TOOLS["metrics"] = [
    "mcp__pm_tools__list_linear_issues",
    "Read",
    "Bash",  # For querying analytics DBs
]

AGENTS["metrics"] = AgentDefinition(
    description="Metrics analyst. Use for velocity, cycle time, etc.",
    prompt="Calculate and explain product metrics...",
    tools=AGENT_TOOLS["metrics"],
    model="sonnet",
)
```

## Key SDK Concepts

- **`AgentDefinition.tools`**: List of allowed tool names. If omitted, agent inherits all tools.
- **`ClaudeAgentOptions.mcp_servers`**: Global MCP server definitions. All agents can potentially access them unless restricted via `tools`.
- **`ClaudeAgentOptions.allowed_tools`**: Restricts orchestrator's direct access (subagents are separate).

## References

- [Claude Agent SDK - Subagents](https://platform.claude.com/docs/en/agent-sdk/subagents.md)
- [Claude Agent SDK - Custom Tools](https://platform.claude.com/docs/en/agent-sdk/custom-tools.md)
- [Linear GraphQL API](https://linear.app/developers/graphql)

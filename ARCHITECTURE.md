# Architecture: AI PM Agent

**Status:** v3 — updated to reflect Track A implementation (Claude Agent SDK merged)
**Last updated:** Feb 14, 2026
**Hackathon deadline:** Feb 16, 3:00 PM EST (~1.5 days remaining)
**Team:** Solo

---

## v3 Revision Summary (Feb 14, 2026)

Track A (Agent SDK + MCP) is **merged to main** and working. Updated this doc to reflect what's actually built vs. what was planned. Key changes:

**1. No `allowed_tools` whitelist.** Removed — was blocking MCP tool discovery. `bypassPermissions` mode handles everything.

**2. Session-scoped client reuse.** `ClaudeSDKClient` instances are kept alive per session via `_clients` dict in `agent.py`. The CLI subprocess maintains full conversation history. Broken clients are evicted and recreated on error.

**3. SDK fork dependency.** Using `naga-k/claude-agent-sdk-python` branch `fix/558-message-buffer-deadlock` to fix a buffer deadlock bug. Installed via `[tool.uv.sources]` git override.

**4. Three-layer bridge pattern.** `routes/chat.py` → `agent.py generate_response()` → `sse_bridge.py`. Each layer is independently testable. 58 backend tests passing.

**5. Duplicate text suppression.** SDK emits both StreamEvent deltas and AssistantMessage TextBlocks. `has_streamed_text` flag prevents double-emitting.

---

## v2 Revision Summary (Feb 12, 2026)

After verifying against the latest Claude Agent SDK docs (Feb 2026), MCP spec (2025-03-26), and Vercel AI SDK v5/v6, several significant architectural changes were made:

**1. Claude Agent SDK IS the orchestrator (not a wrapper we build around).**
The SDK provides `ClaudeSDKClient` for continuous conversations and `query()` for one-off tasks. It handles the agent loop, tool execution, compaction, streaming, and subagent orchestration natively. We define subagents via `AgentDefinition` — the SDK invokes them via the `Task` tool. We do NOT build a custom OrchestratorAgent class.

**2. MCP transport: Streamable HTTP replaces SSE.**
The MCP protocol revision 2025-03-26 deprecated the old SSE transport. The Agent SDK supports three MCP config types: `McpStdioServerConfig` (local, recommended for hackathon), `McpHttpServerConfig` (Streamable HTTP, recommended for production), and `McpSdkServerConfig` (in-process via `@tool` decorator).

**3. FastAPI becomes a thin bridge, not an orchestration layer.**
FastAPI's job: receive HTTP requests from frontend, pass them to `ClaudeSDKClient`, bridge `StreamEvent` messages to frontend via SSE. All agent logic lives in the SDK configuration, not in custom Python classes.

**4. Vercel AI SDK v5+ with redesigned useChat.**
`useChat` now uses UIMessage (frontend state) vs ModelMessage (sent to LLM) separation. Tool invocations have type-specific part identifiers. Custom transports are supported.

**5. Custom tools via `@tool` decorator + `create_sdk_mcp_server()`.**
For PM-specific tools (save_to_memory, cite_source), we use the SDK's `@tool` decorator to create in-process MCP servers — no external process needed.

**6. Agent Teams (new in Feb 2026).**
Opus 4.6 introduced an "Agent Teams" research preview for multi-agent collaboration. For now, we use the simpler subagent pattern (sufficient for our use case). Agent Teams are a post-hackathon upgrade if we need agents to debate/challenge each other.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [System Overview](#2-system-overview)
3. [Tech Stack Decisions](#3-tech-stack-decisions)
4. [Agent Architecture](#4-agent-architecture)
5. [Memory & Persistence Layer](#5-memory--persistence-layer)
6. [MCP Integration Layer](#6-mcp-integration-layer)
7. [Backend Architecture (FastAPI)](#7-backend-architecture-fastapi)
8. [Frontend Architecture (Next.js)](#8-frontend-architecture-nextjs)
9. [Data Flow & API Contracts](#9-data-flow--api-contracts)
10. [Deployment Strategy](#10-deployment-strategy)
11. [Hackathon Scope & Phasing](#11-hackathon-scope--phasing)
12. [Risk Register & Mitigations](#12-risk-register--mitigations)
13. [Open Decisions](#13-open-decisions)

---

## 1. Design Principles

These principles govern every architectural decision. When in doubt, refer back here.

**P1: Context engineering over prompt engineering.** Every token in the context window must justify its existence. We optimize for the smallest set of high-signal tokens that maximize the likelihood of the desired agent behavior. This means just-in-time information loading, aggressive compaction, and structured memory — not dumping everything into the prompt.

**P2: Simple, composable patterns first.** Per Anthropic's guidance: the most successful agent implementations use simple, composable patterns — not complex frameworks. We use the five workflow patterns (chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer) as building blocks and only add complexity when a simpler pattern fails.

**P3: Orchestrator-worker, not monolith.** A lead agent coordinates while specialized subagents handle focused tasks in isolated context windows. This mirrors how PM teams work and solves the context rot problem — subagents use their own windows and only return relevant results to the orchestrator.

**P4: Ground truth at every step.** Agents must gain ground truth from the environment at each step (tool call results, API responses, data from integrations). No hallucinated metrics, no ungrounded recommendations. Every claim cites a source.

**P5: Build for demo, design for production.** The hackathon demo must work reliably. Architectural decisions should be sound enough to extend post-hackathon, but we don't over-engineer what we don't need in 3.5 days.

**P6: Showcase Opus 4.6 strengths.** 1M token context window, 128K output tokens, deep reasoning on complex trade-offs, and multi-agent orchestration quality. These are our differentiators — the architecture should make them visible.

---

## 2. System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                         │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Chat UI  │  │ Source Cards │  │ Agent     │  │ Integration  │  │
│  │ (primary)│  │ & Citations  │  │ Activity  │  │ Status Panel │  │
│  │          │  │              │  │ Stream    │  │              │  │
│  └────┬─────┘  └──────────────┘  └───────────┘  └──────────────┘  │
│       │              SSE (Server-Sent Events)                      │
└───────┼────────────────────────────────────────────────────────────┘
        │ HTTPS
┌───────┼────────────────────────────────────────────────────────────┐
│       ▼           BACKEND (FastAPI)                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    API Gateway Layer                         │   │
│  │  /chat  /sessions  /integrations  /health  /agents/status   │   │
│  └────┬────────────────────────────────────────────────────────┘   │
│       │                                                            │
│  ┌────▼────────────────────────────────────────────────────────┐   │
│  │                  Session Manager                             │   │
│  │  - Conversation state (Redis)                               │   │
│  │  - Agent lifecycle management                               │   │
│  │  - SSE stream multiplexing                                  │   │
│  └────┬────────────────────────────────────────────────────────┘   │
│       │                                                            │
│  ┌────▼────────────────────────────────────────────────────────┐   │
│  │               ORCHESTRATOR AGENT (Opus 4.6)                  │   │
│  │  - Receives user message + session context                  │   │
│  │  - Plans which subagents to invoke                          │   │
│  │  - Delegates tasks, collects results                        │   │
│  │  - Synthesizes final response with citations                │   │
│  │  - Manages compaction & memory writes                       │   │
│  └────┬──────────┬──────────┬──────────┬───────────────────────┘   │
│       │          │          │          │                            │
│  ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐ ┌─▼────────┐                   │
│  │Research│ │Backlog │ │Priorit-│ │  Doc     │                    │
│  │ Agent  │ │ Agent  │ │ization │ │  Agent   │                    │
│  │(Sonnet)│ │(Sonnet)│ │ Agent  │ │ (Opus)  │                    │
│  │        │ │        │ │(Opus)  │ │          │                    │
│  └───┬────┘ └───┬────┘ └───┬────┘ └────┬─────┘                   │
│      │          │          │           │                           │
│  ┌───▼──────────▼──────────▼───────────▼───────────────────────┐   │
│  │                   MCP Integration Layer                      │   │
│  │  ┌───────┐  ┌───────┐  ┌────────┐  ┌─────┐  ┌───────────┐  │   │
│  │  │ Slack │  │Linear │  │ Notion │  │ Web │  │ Amplitude │  │   │
│  │  │  MCP  │  │  MCP  │  │  MCP   │  │Search│ │   MCP     │  │   │
│  │  └───────┘  └───────┘  └────────┘  └─────┘  └───────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 PERSISTENCE LAYER                            │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │   │
│  │  │  Redis   │  │  SQLite/     │  │  File-based Memory    │  │   │
│  │  │ (cache,  │  │  PostgreSQL  │  │  (structured notes,   │  │   │
│  │  │  session │  │  (sessions,  │  │   product knowledge,  │  │   │
│  │  │  state)  │  │   history)   │  │   decision log)       │  │   │
│  │  └──────────┘  └──────────────┘  └───────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack Decisions

### Frontend

| Choice | Why | Alternative Considered |
|--------|-----|----------------------|
| **Next.js 15 (App Router)** | React framework with SSR, API routes, and the ecosystem we need. App Router for server components and streaming. | Remix, Vite+React — Next.js has the most mature AI SDK integration |
| **Tailwind CSS** | Utility-first, fast to iterate, no context-switching to CSS files | styled-components — too slow for hackathon |
| **shadcn/ui** | Polished, accessible components. Copy-paste model means we own the code. | Radix, MUI — shadcn is the fastest path to a premium look |
| **Vercel AI SDK v5+** | Redesigned `useChat` with UIMessage/ModelMessage separation, type-safe tool invocations, custom transport support, `@ai-sdk/anthropic` provider. v5 released Jul 2025; v6 adds per-tool strict mode. | Custom SSE — AI SDK handles edge cases we'd waste time on |

### Backend

| Choice | Why | Alternative Considered |
|--------|-----|----------------------|
| **FastAPI (Python)** | Long-running agent tasks exceed Vercel's timeout limits. FastAPI handles async natively, streams SSE, and has excellent typing. Python aligns with Claude Agent SDK. | Express.js — Claude Agent SDK is Python/TS, but Python has better data science tooling if we need it |
| **Claude Agent SDK (Python)** | The official agent harness (renamed from Claude Code SDK). `ClaudeSDKClient` for continuous conversations, `query()` for one-off tasks. Built-in tools (Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch), subagent orchestration via `AgentDefinition` + `Task` tool, MCP integration via `mcp_servers` config, hooks for pre/post tool use, streaming via `include_partial_messages`, session resume/fork, `max_budget_usd` for cost control, `output_format` for structured JSON output. Install: `uv add claude-agent-sdk`. | Raw Anthropic API — too much boilerplate for agent orchestration |
| **Redis** | In-memory speed for session state, conversation cache, and rate limiting. Sub-millisecond latency. Already proven for agent memory at scale. | Just SQLite — too slow for real-time session state |
| **SQLite (hackathon) → PostgreSQL (production)** | Conversation history, user sessions, integration configs. SQLite for zero-config hackathon; Postgres for cloud. | MongoDB — SQL is simpler for relational session data |

### Agent Models

| Agent | Model | Reasoning |
|-------|-------|-----------|
| **Orchestrator** | Opus 4.6 | Needs the deepest reasoning to plan, delegate, and synthesize across subagent outputs. This is where the 1M context window shines — loading full product context. |
| **Research Agent** | Sonnet 4.5 | High volume of MCP calls, needs to be fast. Sonnet is capable enough for search+synthesize tasks and much cheaper. |
| **Backlog Agent** | Sonnet 4.5 | Reads Linear data, structures it. Doesn't need Opus-level reasoning. |
| **Prioritization Agent** | Opus 4.6 | Weighing incomplete, contradictory evidence is Opus's strength. Complex trade-off reasoning. |
| **Doc Agent** | Opus 4.6 | Generating comprehensive, grounded PRDs and reports. Benefits from 128K output tokens for full documents in a single pass. |

**Cost note:** $500 in API credits. Opus 4.6 is expensive. Use Sonnet for high-frequency, lower-complexity subagents. Reserve Opus for orchestration, prioritization, and document generation.

---

## 4. Agent Architecture

### 4.1 Orchestrator Design (Using Claude Agent SDK)

The orchestrator is NOT a custom Python class we build. It IS Claude (Opus 4.6) running inside the Claude Agent SDK's `ClaudeSDKClient`. We configure it with a system prompt, subagent definitions, MCP servers, and custom tools. The SDK handles the agent loop, tool execution, compaction, and streaming natively.

Claude autonomously decides when to invoke subagents based on each subagent's `description` field, or we can explicitly request them via the prompt.

```python
# Actual implementation — see backend/app/agent.py for full source
from claude_agent_sdk import (
    AgentDefinition, AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient,
    ClaudeSDKError, ResultMessage, TextBlock, ToolResultBlock, ToolUseBlock,
    create_sdk_mcp_server, tool,
)
from claude_agent_sdk.types import StreamEvent, ThinkingConfigAdaptive

# --- Custom PM tools (in-process MCP server) ---

@tool("read_product_context", "Read the current product context and accumulated knowledge", {})
async def read_product_context(args: dict) -> dict:
    context_path = MEMORY_DIR / "product-context.md"
    if context_path.exists():
        text = context_path.read_text()
    else:
        text = "(No product context file found.)"
    return {"content": [{"type": "text", "text": text}]}

@tool("save_insight", "Save a product insight to persistent memory", {
    "category": str,  # "feedback" | "decision" | "metric" | "competitive"
    "content": str,
    "sources": str,   # comma-separated source URLs
})
async def save_insight(args: dict) -> dict:
    category = args["category"]
    if not re.match(r"^[a-zA-Z0-9_-]+$", category):  # Path traversal protection
        return {"content": [{"type": "text", "text": f"Invalid category: {category}"}]}
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

# --- Subagent Definitions ---
# Note: No `tools` whitelist — bypassPermissions mode allows all tools.
# Subagents inherit access to MCP servers from the orchestrator.

AGENTS = {
    "research": AgentDefinition(
        description="Research specialist. Use for finding discussions, feedback, and "
                    "context from Slack, web, and other sources.",
        prompt="You are a research agent for a PM team. Find and synthesize "
               "information from Slack, web, and other sources.\n"
               "Return structured findings with sources. Be thorough but concise.",
        model="sonnet",
    ),
    "backlog": AgentDefinition(
        description="Backlog analyst. Use for reading project state from Linear: "
                    "current sprint, tickets, blockers, velocity.",
        prompt="You are a backlog analyst. Read and structure project state from Linear.\n"
               "Summarize ticket status, blockers, velocity, and key metrics.",
        model="sonnet",
    ),
    "prioritization": AgentDefinition(
        description="Prioritization expert. Use when the user needs help ranking, "
                    "scoring, or deciding between options.",
        prompt="You are a prioritization expert. Apply RICE or impact-effort frameworks.\n"
               "Cite evidence for and against each option. Flag trade-offs.",
        model="opus",
    ),
    "doc-writer": AgentDefinition(
        description="Document generator. Use for creating PRDs, stakeholder updates, "
                    "sprint summaries. Produces publication-ready markdown.",
        prompt="You are a document specialist. Generate well-structured, grounded documents.\n"
               "Include citations for all claims. Keep it concise and actionable.",
        model="opus",
    ),
}

# --- Options factory ---
# MCP servers are conditionally added based on available credentials.
# No `allowed_tools` whitelist — bypassPermissions handles it.

def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=settings.anthropic_model_opus,
        agents=AGENTS,
        mcp_servers=_build_mcp_servers(),          # pm_tools + slack/linear if configured
        permission_mode="bypassPermissions",        # Hackathon — auto-approve all tools
        max_turns=settings.max_turns,
        max_budget_usd=settings.max_budget_per_session_usd,
        include_partial_messages=True,              # Stream partial text/thinking deltas
        thinking=ThinkingConfigAdaptive(type="adaptive"),
        cwd=str(MEMORY_DIR.parent),
        env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
        stderr=_stderr_callback,
    )
```

**Key insight:** We don't write orchestration logic. Claude (Opus 4.6) IS the orchestrator. It reads the subagent descriptions and autonomously decides when to delegate. The SDK handles the agent loop, tool execution, context management, and compaction.

### 4.2 Subagent Specifications

Each subagent is defined with clear boundaries following Anthropic's guidance: single goal, specific tools, defined output format.

#### Research Agent
- **Goal:** Synthesize information from external sources into a structured research brief
- **Model:** Sonnet 4.5
- **MCP tools:** Slack (search channels, read threads), Web Search, Notion (search docs)
- **Input:** Research query + relevant context from orchestrator
- **Output format:**
  ```json
  {
    "summary": "2-3 sentence overview",
    "findings": [
      {
        "source": "slack|notion|web",
        "source_url": "...",
        "key_insight": "...",
        "relevance_score": 0.0-1.0,
        "raw_excerpt": "..."
      }
    ],
    "patterns": ["pattern1", "pattern2"],
    "contradictions": ["if any"],
    "confidence": "high|medium|low",
    "gaps": ["what we couldn't find"]
  }
  ```

#### Backlog Agent
- **Goal:** Read and structure project state from Linear
- **Model:** Sonnet 4.5
- **MCP tools:** Linear (read issues, projects, cycles, labels, assignments)
- **Input:** Query about project state + optional filters
- **Output format:**
  ```json
  {
    "summary": "current sprint/project state overview",
    "tickets": [
      {
        "id": "...",
        "title": "...",
        "status": "...",
        "priority": "...",
        "assignee": "...",
        "labels": [],
        "url": "..."
      }
    ],
    "blockers": [],
    "recently_completed": [],
    "metrics": {
      "velocity": "...",
      "open_count": 0,
      "blocked_count": 0
    }
  }
  ```

#### Prioritization Agent
- **Goal:** Combine signals from other agents and help rank/score/decide
- **Model:** Opus 4.6
- **MCP tools:** None directly — works with outputs from other agents
- **Input:** Research brief + backlog state + user's prioritization question
- **Output format:**
  ```json
  {
    "recommendation": "...",
    "ranked_items": [
      {
        "item": "...",
        "score": 0.0,
        "evidence_for": ["..."],
        "evidence_against": ["..."],
        "confidence": "high|medium|low"
      }
    ],
    "framework_used": "RICE|impact-effort|custom",
    "trade_offs": ["..."],
    "open_questions": ["..."]
  }
  ```

#### Doc Agent
- **Goal:** Generate grounded documents (PRDs, updates, one-pagers)
- **Model:** Opus 4.6
- **MCP tools:** Notion (create/update pages), Slack (post updates)
- **Input:** Research brief + backlog state + prioritization output + doc type + audience
- **Output format:** Structured markdown with citations, ready to push to Notion/Slack

### 4.3 Context Engineering Strategy

This is critical. Applying Anthropic's context engineering principles:

**System prompt design:** Orchestrator gets a focused system prompt at the "right altitude" — not over-specified brittle logic, not vague. It describes the orchestrator's role, available subagents, output expectations, and memory access patterns. No hardcoded decision trees.

**Tool design:** Each tool is self-contained, non-overlapping, and purpose-specific. Tool descriptions are concise — every unnecessary word in a tool description steals attention from the actual task.

**Just-in-time loading:** We do NOT dump all product context into the prompt upfront. Instead:
- The orchestrator gets a lightweight context summary (session state, recent memory, integration status)
- Subagents pull specific data on demand via MCP tools
- Only relevant results flow back to the orchestrator

**Compaction strategy:**
- Use server-side compaction (Opus 4.6 supports it)
- Trigger compaction earlier rather than later — reserve ~30% of context window as free working memory
- After compaction, critical context is preserved via structured notes in the memory system
- Tool results from deep in the history are cleared after their insights are captured

**Subagent context isolation:** Each subagent operates in its own context window. This is our primary defense against context rot. The orchestrator passes only the relevant slice of context to each subagent, and subagents return only structured results — not their full reasoning chain.

```
Context Budget (Orchestrator - Opus 4.6, 1M tokens):
├── System prompt:              ~2K tokens
├── Session memory (loaded):    ~5-10K tokens
├── Conversation history:       ~20-50K tokens (compacted)
├── Active subagent results:    ~10-20K tokens
├── MCP tool descriptions:      ~3K tokens
└── FREE WORKING MEMORY:        ~900K+ tokens available
    (this is where Opus 4.6's 1M window shines)
```

### 4.4 Agent Communication Protocol (SDK-native)

Subagents are invoked via the SDK's `Task` tool. Claude automatically uses it when it decides delegation is needed. The SDK handles the full lifecycle.

```python
# How subagent invocation actually works in the SDK:

# 1. Claude (orchestrator) decides to invoke a subagent by calling the Task tool:
#    ToolUseBlock(name="Task", input={
#        "description": "Research sprint priorities",
#        "prompt": "Find discussions about sprint priorities in Slack",
#        "subagent_type": "research"   # matches key in agents dict
#    })

# 2. SDK spawns the subagent in an ISOLATED context window
#    - Gets its own system prompt (from AgentDefinition.prompt)
#    - Gets only the tools listed in AgentDefinition.tools
#    - Uses the model specified in AgentDefinition.model
#    - Has NO access to the orchestrator's conversation history

# 3. Subagent runs autonomously, making tool calls as needed
#    - All messages have parent_tool_use_id set (for tracking)
#    - StreamEvent messages flow through for real-time monitoring

# 4. Subagent returns result as a ToolResultBlock to orchestrator
#    - Result includes: text summary, agentId (for resume), usage stats

# 5. Orchestrator receives result and continues its own reasoning

# Detecting subagent events in the stream:
async for msg in client.receive_response():
    if isinstance(msg, StreamEvent):
        if msg.parent_tool_use_id:
            # This event is from inside a subagent — we skip these
            # to avoid streaming subagent text to the frontend
            continue

    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, ToolUseBlock) and block.name == "Task":
                agent_type = block.input.get("subagent_type")
                print(f"Orchestrator invoking subagent: {agent_type}")
```

**Important SDK constraints:**
- Subagents CANNOT spawn their own subagents (no nested delegation)
- Don't include `Task` in a subagent's `tools` array
- Subagent transcripts persist independently and survive main conversation compaction
- **Session-scoped client reuse** — `ClaudeSDKClient` instances are kept alive per session in `agent.py._clients`. Multi-turn context is maintained by the CLI subprocess. Broken clients are evicted and recreated automatically.
- We also depend on a fork branch (`fix/558-message-buffer-deadlock`) that fixes a buffer deadlock bug (#558) in the SDK's message stream

---

## 5. Memory & Persistence Layer

### 5.1 Memory Architecture Overview

We use a **three-tier memory system** inspired by Anthropic's recommendations and Mem0's architecture:

```
┌──────────────────────────────────────────────────────────┐
│                    MEMORY TIERS                          │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ TIER 1: Working Memory (Redis)                      │ │
│  │ - Current session state                             │ │
│  │ - Active conversation context                       │ │
│  │ - Subagent task queue & results                     │ │
│  │ - TTL: session duration (auto-expire)               │ │
│  │ - Latency: <1ms                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ TIER 2: Session Memory (SQLite/Postgres)            │ │
│  │ - Conversation history (compacted)                  │ │
│  │ - User preferences & settings                       │ │
│  │ - Integration configs & auth tokens                 │ │
│  │ - Agent execution logs                              │ │
│  │ - TTL: persistent                                   │ │
│  │ - Latency: <10ms                                    │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ TIER 3: Product Knowledge Memory (File-based)       │ │
│  │ - Accumulated product insights                      │ │
│  │ - Decision log (what was decided, why, when)        │ │
│  │ - Metric baselines & trends                         │ │
│  │ - Research synthesis (persistent insights)          │ │
│  │ - Entity relationships (lightweight graph)          │ │
│  │ - TTL: permanent, grows over time                   │ │
│  │ - Loaded just-in-time by orchestrator               │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 5.2 Why NOT a Vector DB for the Hackathon

**Decision: Skip vector DB / RAG for MVP. Use structured file-based memory + Redis.**

Reasoning:
- **Vector DBs add infra complexity** — setting up Qdrant/Pinecone/Chroma, managing embeddings, tuning retrieval is a full day of work we don't have.
- **Our data is already structured** — Linear tickets, Slack messages, and Notion docs come with metadata (timestamps, authors, labels, channels). Structured queries beat semantic search here.
- **MCP handles retrieval** — Slack MCP, Linear MCP, and Notion MCP already have search endpoints. We're using the source tools' own search rather than re-indexing their data.
- **Opus 4.6's 1M context window reduces the need for RAG** — we can load significantly more raw context than any other model. Where smaller models need RAG to work within 128K, Opus can hold entire project states directly.
- **Mem0 / graph memory is a post-hackathon enhancement** — the file-based structured notes pattern (recommended by Anthropic for Claude agents) is simpler and good enough for a demo.

**Post-hackathon upgrade path:** Add Mem0 with Redis backend for persistent cross-session memory with automatic extraction and conflict resolution. Add graph memory (Mem0g) if entity relationships become important (e.g., "which decisions affected which features").

### 5.3 File-Based Product Knowledge Memory

Following Anthropic's "structured note-taking" pattern:

```
/memory/
├── product-context.md        # Product overview, team, OKRs (loaded always)
├── decisions/
│   ├── 2026-02-12-auth.md    # Decision: chose JWT over sessions
│   └── ...                   # Each decision: what, why, when, who, outcome
├── insights/
│   ├── user-feedback.md      # Synthesized feedback patterns
│   ├── competitive.md        # Competitive intelligence
│   └── metrics-baseline.md   # Key metric baselines & trends
├── session-notes/
│   └── {session-id}.md       # Per-session structured notes (auto-generated)
└── entity-index.json         # Lightweight entity graph (features, people, decisions)
```

The orchestrator checks `product-context.md` and `entity-index.json` at the start of each session (~5-10K tokens). Other files are loaded just-in-time based on the query.

### 5.4 Redis Schema

```python
# Session state (per active session)
session:{session_id}:state       → JSON (current conversation state)
session:{session_id}:messages    → List (recent message history, pre-compaction)
session:{session_id}:agents      → Hash (active subagent statuses)

# Cache (shared across sessions)
cache:slack:{channel}:{query}    → JSON (cached Slack search results, TTL: 5min)
cache:linear:{query}             → JSON (cached Linear queries, TTL: 2min)
cache:research:{hash}            → JSON (cached research briefs, TTL: 30min)

# Rate limiting
ratelimit:anthropic:{minute}     → Counter (API call rate limiting)
ratelimit:mcp:{provider}:{min}   → Counter (per-integration rate limits)
```

---

## 6. MCP Integration Layer

### 6.1 MCP Architecture

MCP (Model Context Protocol, spec revision 2025-03-26) is our universal connector layer. The Claude Agent SDK manages MCP connections natively via the `mcp_servers` config.

**Transport types (current spec):**
- **stdio** — local subprocess communication (recommended for hackathon — simplest)
- **Streamable HTTP** — replaces the deprecated SSE transport. Recommended for production remote servers.
- **SDK in-process** — custom tools via `@tool` decorator + `create_sdk_mcp_server()`. Zero overhead.

```python
# MCP server configs in the Claude Agent SDK
mcp_servers = {
    # stdio: local process (hackathon — simplest setup)
    "slack": {
        "command": "npx",
        "args": ["@anthropic/slack-mcp"],
        "env": {"SLACK_BOT_TOKEN": "..."}
    },
    # Streamable HTTP: remote server (production)
    "linear-remote": {
        "type": "http",
        "url": "https://my-linear-mcp.railway.app/mcp",
        "headers": {"Authorization": "Bearer ..."}
    },
    # In-process: custom tools (zero overhead)
    "pm-memory": create_sdk_mcp_server(
        name="pm-memory", tools=[save_insight, read_product_context]
    ),
}
```

**Note:** The old SSE transport (`type: "sse"`) is deprecated in the MCP spec but still supported for backward compatibility. We use **stdio** for the hackathon (simplest) and can upgrade to Streamable HTTP for production.

### 6.2 Hackathon MCP Scope

**Must ship (Day 1-2):**

| Integration | MCP Server | Key Tools | Auth |
|-------------|-----------|-----------|------|
| **Linear** | `@anthropic/linear-mcp` or custom | `search_issues`, `get_issue`, `list_projects`, `list_cycles`, `get_project_status` | API key |
| **Slack** | `@anthropic/slack-mcp` or custom | `search_messages`, `read_thread`, `list_channels`, `post_message` | Bot token (OAuth) |

**Should ship (Day 2-3):**

| Integration | MCP Server | Key Tools | Auth |
|-------------|-----------|-----------|------|
| **Web Search** | Custom (Brave/Tavily API) | `web_search`, `fetch_page` | API key |
| **Notion** | `@anthropic/notion-mcp` or custom | `search_pages`, `read_page`, `create_page` | Integration token |

**Demo-ready placeholder (Day 3 — UI only, not wired):**

| Integration | Status in UI |
|-------------|-------------|
| Amplitude | "Coming soon" badge |
| Figma | "Coming soon" badge |
| Intercom | "Coming soon" badge |

### 6.3 MCP Tool Design Principles

Per context engineering best practices, tool descriptions must be concise and non-overlapping:

```python
# GOOD — concise, specific, self-contained
{
    "name": "slack_search_messages",
    "description": "Search Slack messages by keyword. Returns messages with channel, author, timestamp, and thread context. Use for finding discussions, decisions, or feedback.",
    "parameters": {
        "query": "Search keywords",
        "channels": "Optional: comma-separated channel names to scope search",
        "limit": "Max results (default 20)",
        "after": "Optional: ISO date to filter messages after"
    }
}

# BAD — verbose, overlapping, wastes context tokens
{
    "name": "search_slack_for_messages_and_threads",
    "description": "This tool allows you to search through Slack workspace messages. You can use it to find messages that match certain keywords. The tool will search across all channels the bot has access to, or you can specify particular channels. Results include the message text, the channel it was posted in, who posted it, when it was posted, and any thread replies. This is useful for finding past discussions about features, decisions that were made, customer feedback that was shared in channels, and other historical context that might be relevant to the current task..."
}
```

### 6.4 MCP Error Handling & Fallbacks

The Claude Agent SDK handles MCP tool call execution internally. We add error handling via **hooks** rather than wrapping tool calls:

```python
from claude_agent_sdk import HookMatcher, HookContext
from typing import Any

async def mcp_error_handler(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """PostToolUse hook: log MCP errors and provide fallback guidance."""
    tool_response = input_data.get("tool_response", "")
    tool_name = input_data.get("tool_name", "")

    if isinstance(tool_response, dict) and tool_response.get("is_error"):
        error_msg = str(tool_response.get("content", "Unknown error"))
        print(f"[MCP ERROR] {tool_name}: {error_msg}")

        # Return a system message guiding the agent to handle gracefully
        return {
            "systemMessage": f"The {tool_name} tool returned an error: {error_msg}. "
                           f"Continue with available information and note the gap."
        }
    return {}

async def mcp_rate_limit_guard(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """PreToolUse hook: rate limit MCP calls to avoid API throttling."""
    tool_name = input_data.get("tool_name", "")
    if tool_name.startswith("mcp__"):
        # Simple in-memory rate limiting
        # (for hackathon; use Redis for production)
        pass
    return {}

# Register hooks in ClaudeAgentOptions:
# hooks={
#     "PostToolUse": [HookMatcher(matcher="mcp__*", hooks=[mcp_error_handler])],
#     "PreToolUse": [HookMatcher(matcher="mcp__*", hooks=[mcp_rate_limit_guard])],
# }
```

---

## 7. Backend Architecture (FastAPI)

### 7.1 Project Structure (Simplified — SDK does the heavy lifting)

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry + CORS + lifecycle
│   ├── config.py               # Environment config, API keys
│   ├── agent.py                # Claude Agent SDK setup (THE core file)
│   │                           # - ClaudeSDKClient config
│   │                           # - AgentDefinition for each subagent
│   │                           # - MCP server configs
│   │                           # - Custom @tool definitions
│   │                           # - Hooks (error handling, logging)
│   ├── routes/
│   │   ├── chat.py             # POST /chat → SSE bridge to SDK
│   │   ├── sessions.py         # Session lifecycle (connect/disconnect)
│   │   └── health.py           # Health checks + integration status
│   ├── sse_bridge.py           # StreamEvent → SSE event translation
│   └── models.py               # Pydantic schemas for API
├── memory/                     # Product knowledge files (persisted)
│   ├── product-context.md
│   ├── decisions/
│   ├── insights/
│   └── entity-index.json
├── tests/                      # pytest tests — 58 passing (pytest-asyncio + httpx)
│   ├── conftest.py             # Shared fixtures (async client, SDK mocks)
│   ├── test_health.py          # Health endpoint tests
│   ├── test_sessions.py        # Session CRUD tests
│   ├── test_chat.py            # SSE streaming, error handling, input validation tests
│   └── test_models.py          # Pydantic model tests
├── pyproject.toml              # Project metadata + deps (managed by uv)
├── Dockerfile
└── docker-compose.yml          # Backend + Redis (optional for hackathon)
```

**Note how much simpler this is than v1.** No custom orchestrator, no MCP client wrapper, no compaction helpers, no tool registry. The SDK handles all of that. The backend is ~4 files of real logic.

### 7.2 API Design

#### Core Endpoints (implemented)

```
POST   /api/chat                    # Send message → SSE streaming response
POST   /api/sessions                # Create new session
GET    /api/sessions/{id}           # Get session state
DELETE /api/sessions/{id}           # End session
GET    /api/health                  # System health check
```

#### Planned Endpoints (not yet implemented)

```
GET    /api/integrations            # List configured integrations
POST   /api/integrations/{provider} # Connect an integration
DELETE /api/integrations/{provider} # Disconnect
GET    /api/integrations/{provider}/status # Health check
```

#### Chat Endpoint (the core flow — actual implementation)

The architecture uses a **three-layer bridge**: `routes/chat.py` → `agent.py` → `sse_bridge.py`.

```python
# routes/chat.py — ultra-thin, delegates everything
@router.post("/api/chat")
async def chat(request: ChatRequest) -> EventSourceResponse:
    event_source = generate_response(
        message=request.message,
        session_id=request.session_id,
        context=request.context,
    )
    return EventSourceResponse(
        stream_sse_events(event_source),
        media_type="text/event-stream",
    )
```

```python
# agent.py — generate_response() is the critical interface
# Reuses ClaudeSDKClient per session for multi-turn conversation context
async def generate_response(message, session_id, context=None):
    client = await _get_or_create_client(session_id)
    try:
        await client.query(message, session_id=session_id)

        async for msg in client.receive_response():
            if isinstance(msg, StreamEvent):
                # Stream orchestrator text deltas (skip subagent text)
                if not msg.parent_tool_use_id:
                    delta = msg.event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield ("text", json.dumps(delta["text"]))
                    elif delta.get("type") == "thinking_delta":
                        yield ("thinking", ThinkingEventData(...).model_dump_json())

            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock) and block.name == "Task":
                        yield ("agent_activity", AgentActivityData(...).model_dump_json())
                    elif isinstance(block, ToolUseBlock):
                        yield ("tool_call", ToolCallData(...).model_dump_json())

            elif isinstance(msg, ResultMessage):
                yield ("done", DoneEventData(...).model_dump_json())
    finally:
        await client.disconnect()  # Guaranteed cleanup
```

```python
# sse_bridge.py — translates tuples to ServerSentEvent objects
async def stream_sse_events(event_source):
    async for event_type, json_data in event_source:
        yield ServerSentEvent(event=event_type, data=json_data)
```

**Key design decisions:**
- **Session-scoped client reuse** — `ClaudeSDKClient` instances are kept alive per session in `_clients` dict. Multi-turn context maintained by the CLI subprocess. Broken clients evicted on error.
- **Three-layer bridge** — route handler has zero logic, agent layer handles SDK complexity, SSE bridge handles wire format. Each layer is independently testable.
- **Duplicate text suppression** — StreamEvent deltas and AssistantMessage TextBlocks can emit the same text. `has_streamed_text` flag prevents doubling.
- **Guaranteed done event** — `done_emitted` flag ensures a `done` event is always sent even on exceptions.

### 7.3 Streaming Architecture

```
User sends message
       │
       ▼
  FastAPI receives POST /api/chat
       │
       ▼
  Orchestrator starts (Opus 4.6)
       │
       ├──→ SSE: {"type": "thinking", "data": "Analyzing your request..."}
       │
       ├──→ Spawns Research Agent
       │    ├──→ SSE: {"type": "agent_activity", "agent": "research", "status": "running"}
       │    ├──→ Research Agent calls Slack MCP
       │    ├──→ Research Agent calls Web Search
       │    └──→ SSE: {"type": "agent_activity", "agent": "research", "status": "completed"}
       │
       ├──→ Spawns Backlog Agent (parallel with research)
       │    ├──→ SSE: {"type": "agent_activity", "agent": "backlog", "status": "running"}
       │    ├──→ Backlog Agent calls Linear MCP
       │    └──→ SSE: {"type": "agent_activity", "agent": "backlog", "status": "completed"}
       │
       ├──→ Orchestrator synthesizes results
       │    ├──→ SSE: {"type": "text", "data": "Based on..."} (streaming tokens)
       │    ├──→ SSE: {"type": "citation", "data": {"source": "slack", "url": "..."}}
       │    └──→ SSE: {"type": "text", "data": "...continued response"}
       │
       └──→ SSE: {"type": "done"}
```

---

## 8. Frontend Architecture (Next.js)

### 8.1 Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout with providers
│   ├── page.tsx                # Landing/redirect
│   ├── chat/
│   │   ├── page.tsx            # Main chat interface
│   │   └── layout.tsx          # Chat layout (sidebar + main)
│   └── settings/
│       └── page.tsx            # Integration management
├── components/
│   ├── chat/
│   │   ├── ChatInput.tsx       # Message input with commands
│   │   ├── ChatMessage.tsx     # Single message (user or agent)
│   │   ├── AgentActivity.tsx   # Live agent status indicators
│   │   ├── SourceCard.tsx      # Inline citation/source card
│   │   ├── DataVisualization.tsx # Inline charts/metrics
│   │   └── TicketPreview.tsx   # Linear ticket inline preview
│   ├── sidebar/
│   │   ├── SessionList.tsx     # Past conversations
│   │   ├── IntegrationPanel.tsx # Connected integrations status
│   │   └── QuickActions.tsx    # Common PM actions
│   └── ui/                     # shadcn/ui components
├── hooks/
│   ├── useChat.ts              # SSE chat hook (wraps AI SDK)
│   ├── useAgentStream.ts       # Agent activity stream hook
│   └── useIntegrations.ts      # Integration status hook
├── lib/
│   ├── api.ts                  # API client
│   └── types.ts                # Shared types
├── styles/
│   └── globals.css             # Tailwind + custom styles
├── public/
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

### 8.2 Key UI Components

**Chat Interface (primary):**
- Message input at bottom (like Perplexity/ChatGPT)
- Messages stream in real-time via SSE
- Agent thinking/activity shown as subtle animated indicators
- Rich results: not just text walls — inline source cards, ticket previews, metric cards

**Agent Activity Stream:**
- Small panel (collapsible) showing what each subagent is doing in real-time
- "Research Agent: Searching Slack for 'rate limiting'..."
- "Backlog Agent: Reading Linear project status..."
- Visual feedback that the system is working, not stalled

**Source Cards:**
- Inline cards that show where information came from
- Slack message card (channel, author, timestamp, snippet)
- Linear ticket card (status, priority, assignee)
- Web source card (title, URL, snippet)
- Clickable to open in original tool

**Integration Status Panel (sidebar):**
- Shows which tools are connected with green/red indicators
- "Coming soon" badges for unconnected integrations
- Quick-connect buttons for available integrations

### 8.3 SSE Client Implementation (AI SDK v5 pattern)

AI SDK v5 redesigned `useChat` with UIMessage (frontend state) vs ModelMessage (sent to LLM). For our custom backend (FastAPI), we use a custom transport or build our own hook that consumes SSE from our backend:

```typescript
// hooks/useAgentChat.ts
// Custom hook that connects to our FastAPI SSE backend
// (We can't use AI SDK's useChat directly with a non-standard SSE format,
//  so we build a lightweight custom hook instead)

import { useState, useCallback, useRef } from 'react';

interface AgentActivity {
  agent: string;
  task: string;
  status: 'running' | 'completed';
}

interface Citation {
  type: 'slack' | 'linear' | 'web';
  url: string;
  title: string;
  snippet: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
}

export function useAgentChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [agentActivity, setAgentActivity] = useState<AgentActivity[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionCost, setSessionCost] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    setIsStreaming(true);
    const msgId = crypto.randomUUID();

    // Add user message immediately
    setMessages(prev => [...prev, { id: msgId, role: 'user', content, citations: [] }]);

    // Create assistant message placeholder
    const assistantId = crypto.randomUUID();
    let assistantContent = '';
    const citations: Citation[] = [];

    setMessages(prev => [...prev, {
      id: assistantId, role: 'assistant', content: '', citations: []
    }]);

    // POST to our FastAPI backend, receive SSE stream
    abortRef.current = new AbortController();
    const response = await fetch(`/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: content }),
      signal: abortRef.current.signal,
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventType = line.slice(7);
          // Next line is data
          continue;
        }
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));

          // Handle different event types from our FastAPI SSE bridge
          if (typeof data === 'string') {
            // Text streaming
            assistantContent += data;
            setMessages(prev => prev.map(m =>
              m.id === assistantId ? { ...m, content: assistantContent } : m
            ));
          }
        }
      }
    }

    setIsStreaming(false);
  }, [sessionId]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return { messages, agentActivity, isStreaming, sessionCost, sendMessage, stop };
}
```

**Alternative (simpler for hackathon):** Skip Vercel AI SDK entirely and use EventSource directly. The AI SDK v5 is powerful but its custom transport setup adds complexity when our backend isn't a standard AI SDK provider. For a hackathon, a custom ~50-line hook is faster to get working.

---

## 9. Data Flow & API Contracts

### 9.1 Complete Request Flow

```
1. User types: "What should we prioritize for the next sprint?"

2. Frontend → Backend:
   POST /api/chat
   {
     "session_id": "abc-123",
     "message": "What should we prioritize for the next sprint?",
     "context": { "active_project": "API Platform" }
   }

3. Backend: Orchestrator classifies intent → "prioritization"
   Creates plan: [research(parallel) + backlog(parallel)] → prioritization(sequential)

4. Research Agent (Sonnet 4.5):
   → slack_search("sprint priorities", channels=["#api-platform", "#product"])
   → slack_search("user feedback", channels=["#support", "#customer-feedback"])
   → Returns: structured research brief with 8 findings

5. Backlog Agent (Sonnet 4.5):
   → linear_list_issues(project="API Platform", status=["todo", "in_progress", "backlog"])
   → linear_get_cycles(current=true)
   → Returns: 23 tickets, 3 blocked, current velocity metrics

6. Prioritization Agent (Opus 4.6):
   → Receives: research brief + backlog state + session memory
   → Applies RICE scoring with evidence from research
   → Returns: ranked list of 10 items with evidence for/against each

7. Orchestrator (Opus 4.6):
   → Synthesizes all results
   → Generates response with inline citations
   → Writes key insights to memory
   → Streams response via SSE

8. Frontend renders:
   → Streaming text with inline source cards
   → Ranked priority list with expandable evidence
   → Agent activity indicators (completed)
```

### 9.2 SSE Event Types

| Event Type | Payload | When |
|-----------|---------|------|
| `thinking` | `{ "text": "..." }` | Orchestrator is planning |
| `agent_activity` | `{ "agent": "research", "status": "running", "task": "..." }` | Subagent starts/completes |
| `text` | `"string"` | Token-by-token response streaming |
| `citation` | `{ "type": "slack\|linear\|web", "url": "...", "title": "...", "snippet": "..." }` | Inline citation reference |
| `tool_call` | `{ "tool": "slack_search", "params": {...} }` | Agent is calling a tool (for activity display) |
| `error` | `{ "message": "...", "recoverable": true\|false }` | Something went wrong |
| `done` | `{ "tokens_used": ..., "agents_used": [...] }` | Response complete |

---

## 10. Deployment Strategy

### 10.1 Local Development (Day 1-2)

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://redis:6379
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - LINEAR_API_KEY=${LINEAR_API_KEY}
    depends_on: [redis]
    volumes:
      - ./backend/memory:/app/memory  # Persistent memory

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

### 10.2 Cloud Deployment (Day 3 — remote hackathon requirement)

**Target: Railway or Fly.io** (both support Docker, easy to deploy, generous free tiers)

| Component | Deployment | Why |
|-----------|-----------|-----|
| Frontend (Next.js) | Vercel | Zero-config, CDN, perfect for Next.js |
| Backend (FastAPI) | Railway or Fly.io | Supports long-running processes, Docker, persistent volumes |
| Redis | Railway (managed) or Upstash | Managed Redis with persistence |
| Memory files | Persistent volume on Railway | Must survive container restarts |

```
┌─────────────┐     ┌────────────────┐     ┌─────────────┐
│   Vercel     │────▶│  Railway/Fly   │────▶│  Railway     │
│  (Frontend)  │ API │  (FastAPI +    │     │  (Managed    │
│  Next.js     │     │   Agents)      │     │   Redis)     │
└─────────────┘     └────────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │ Persistent  │
                    │ Volume      │
                    │ (memory/)   │
                    └─────────────┘
```

**Deployment checklist:**
- [ ] Environment variables configured (API keys, tokens)
- [ ] CORS configured for Vercel domain
- [ ] SSL/HTTPS on all endpoints
- [ ] Health check endpoint responding
- [ ] Redis connected and persisting
- [ ] Memory volume mounted
- [ ] Cold start time acceptable (<5s)

### 10.3 Environment Variables

```bash
# Anthropic
ANTHROPIC_API_KEY=          # Required: Claude API access
ANTHROPIC_MODEL_OPUS=claude-opus-4-6-20260211  # Orchestrator + complex agents
ANTHROPIC_MODEL_SONNET=claude-sonnet-4-5-20250929  # Fast subagents

# MCP Integrations
SLACK_BOT_TOKEN=            # Required: Slack bot OAuth token
SLACK_SIGNING_SECRET=       # Required: Slack request verification
LINEAR_API_KEY=             # Required: Linear API key
NOTION_INTEGRATION_TOKEN=   # Optional: Notion integration
BRAVE_API_KEY=              # Optional: Web search

# Infrastructure
REDIS_URL=redis://localhost:6379
DATABASE_URL=sqlite:///./data/app.db  # or postgres://...

# App
FRONTEND_URL=http://localhost:3000  # For CORS
SESSION_SECRET=              # Session encryption
LOG_LEVEL=INFO
```

---

## 11. Hackathon Scope & Phasing

### Day-by-Day Plan

#### Day 3 (Feb 12) — Foundation ✅ DONE
**Goal: Backend skeleton + orchestrator + one working subagent**

- [x] Project scaffolding (FastAPI + Next.js monorepo)
- [x] Docker Compose setup (backend + Redis)
- [x] Basic SSE streaming endpoint working
- [x] Minimal chat UI (message input + streaming response)
- [x] Backend tests passing (40 tests)

#### Day 4 (Feb 13) — Agent SDK Integration ✅ DONE
**Goal: Replace scaffold with Claude Agent SDK, multi-agent orchestration**

- [x] Claude Agent SDK integration — orchestrator agent (Opus 4.6) running
- [x] Subagent definitions: research, backlog, prioritization, doc-writer
- [x] MCP integration: Slack + Linear (conditional on credentials)
- [x] Custom PM tools via `@tool` decorator (read_product_context, save_insight)
- [x] Streaming: text deltas, thinking, agent_activity, tool_call events
- [x] Adaptive thinking (`ThinkingConfigAdaptive`)
- [x] Session-scoped client reuse with automatic error recovery
- [x] Error handling: ClaudeSDKError, client eviction, done fallback
- [x] Path traversal protection on save_insight
- [x] Backend tests passing (58 tests)
- **Verified:** Subagent dispatch works (backlog agent ran Glob/Grep/Read/Bash tools)

#### Day 5 (Feb 14, today) — Frontend + Deploy
**Goal: Frontend shows agent activity, deployed for feedback**

- [ ] Agent activity stream (frontend shows what each agent is doing)
- [ ] Source cards / citations in UI
- [ ] Cloud deployment (Railway/Fly + Vercel)
- [ ] UI polish — loading states, thinking indicators, error handling
- [ ] End-to-end testing on deployed environment
- **End of day test:** Full demo flow works on cloud deployment

#### Day 6 (Feb 15-16, morning) — Demo Prep
**Goal: Record demo video, prepare submission**

- [ ] Final UI polish and integration testing
- [ ] Record 3-minute demo video
- [ ] Write 100-200 word summary
- [ ] GitHub repo cleanup (README, .env.example)
- [ ] Submit before 3:00 PM EST

### MVP Feature Matrix

| Feature | Status | Priority |
|---------|--------|----------|
| Chat interface with streaming | ✅ Working | Must Have |
| Claude Agent SDK orchestrator (Opus 4.6) | ✅ Working | Must Have |
| Subagent orchestration (4 agents defined) | ✅ Working | Must Have |
| Linear integration (Backlog Agent via MCP) | ✅ Configured | Must Have |
| Slack integration (Research Agent via MCP) | ✅ Configured | Must Have |
| Adaptive thinking (extended thinking) | ✅ Working | Must Have |
| Custom PM tools (memory read/write) | ✅ Working | Must Have |
| Agent activity stream in UI | 🔧 Backend ready, frontend TODO | Must Have |
| Source cards / citations in UI | 🔧 TODO | Should Have |
| Cloud deployment | 🔧 TODO | Must Have |
| Web search integration | 📋 Planned | Should Have |
| Notion integration | 📋 Planned | Nice to Have |
| Session history | 📋 Planned | Nice to Have |
| E2B sandboxed execution | 📋 Evaluating | Nice to Have |

### What We're NOT Building

- Authentication / user management (single user for demo)
- Multi-tenant / team features
- Amplitude/Mixpanel integration (too complex for hackathon)
- Figma integration
- Any GTM-specific agents (PM-only for MVP)
- Mobile responsiveness (desktop demo only)
- Exhaustive test coverage (focused regression tests, not 100% coverage)

---

## 12. Risk Register & Mitigations

| Risk | Likelihood | Impact | Mitigation | Status |
|------|-----------|--------|-----------|--------|
| **Agent responses too slow** (multi-hop subagents add latency) | High | High | Parallelize subagents where possible. Use Sonnet for fast subagents. Set timeouts. Show agent activity so user knows it's working. | Active |
| **SDK resume broken** (no multi-turn context) | ~~Confirmed~~ Fixed | Medium | Session-scoped client reuse implemented. CLI subprocess maintains conversation history. | Resolved |
| **SDK buffer deadlock** (#558) | Confirmed | High | Using fork branch `fix/558-message-buffer-deadlock`. Draft PR #572 submitted upstream. | Workaround in place |
| **MCP integration breaks during demo** | Medium | High | Cache recent results. Build fallback responses with cached data. Test on actual Linear/Slack data before demo. | Active |
| **Context rot on long conversations** | Medium | Medium | Client reuse means context accumulates. SDK handles compaction internally. Subagent isolation helps. | Active |
| **$500 API credits run out** | Medium | Critical | Use Sonnet for high-volume subagents. Cache aggressively. Monitor spend daily. Per-session budget via `max_budget_usd`. | Active |
| **Cloud deployment issues** | Medium | High | Deploy to cloud on Day 5, not last day. Have Docker Compose local fallback for demo. | Active |
| **Opus 4.6 model availability** | Low | Critical | Fallback to Sonnet 4.5. Model is configurable via env var. | Active |
| **Scope creep** | High | High | This document IS the scope. If it's not in the Day-by-Day Plan, it doesn't get built. | Active |

---

## 13. Decisions Log

### Resolved

1. **Monorepo vs separate repos?** → **Monorepo.** Structure: `/backend` + `/frontend` at root.

2. **Claude Agent SDK (Python) vs TypeScript SDK?** → **Python.** FastAPI alignment, mature async support. Frontend is TypeScript (standard pattern).

3. **Vercel AI SDK data stream protocol vs custom SSE?** → **Custom SSE with fetch-based parser.** Simpler than adapting Vercel AI SDK's data stream protocol to our FastAPI backend. Custom `useChat` hook is ~50 lines. May revisit if we need AI SDK features later.

4. **How much of Linear/Slack to index upfront vs query on demand?** → **Query on demand via MCP.** No upfront indexing. MCP servers handle search.

5. **allowed_tools whitelist vs bypassPermissions?** → **bypassPermissions only, no whitelist.** `allowed_tools` was blocking MCP tools from being discovered. `bypassPermissions` handles everything for hackathon scope.

6. **Session reuse vs fresh client per query?** → **Session-scoped client reuse.** `ClaudeSDKClient` kept alive per session in `_clients` dict. CLI subprocess maintains conversation history. Broken clients evicted and recreated on error.

7. **SDK dependency: upstream vs fork?** → **Fork branch** (`naga-k/claude-agent-sdk-python`, branch `fix/558-message-buffer-deadlock`) via `[tool.uv.sources]` git override. Draft PR #572 submitted upstream. Will switch back to upstream when merged.

### Open

1. **Notion MCP — build custom or use existing?** — Check MCP registry first.

2. **E2B sandboxed execution** — Evaluate for safe tool execution. Could use during hackathon if time permits. See Agent SDK Hosting Guide for sandbox provider options.

3. **Cloud deployment target** — Railway vs Fly.io vs Render for FastAPI backend. Vercel for frontend is decided.

---

## References

### Claude Agent SDK (Primary — build from these)
- [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview) — start here
- [Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) — full API: `query()`, `ClaudeSDKClient`, `AgentDefinition`, hooks, types
- [Subagents in the SDK](https://platform.claude.com/docs/en/agent-sdk/subagents) — how to define and invoke subagents
- [Streaming Output](https://platform.claude.com/docs/en/agent-sdk/streaming-output) — `include_partial_messages`, `StreamEvent`
- [Streaming Input Mode](https://platform.claude.com/docs/en/agent-sdk/streaming-vs-single-mode) — preferred mode for interactive apps
- [SDK GitHub (Python)](https://github.com/anthropics/claude-agent-sdk-python)
- [SDK Demo Agents](https://github.com/anthropics/claude-agent-sdk-demos) — email assistant, research agent examples

### MCP (Model Context Protocol)
- [MCP Transports Spec (2025-03-26)](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports) — Streamable HTTP + stdio
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — v1.x stable, v2 expected Q1 2026
- [Why MCP Deprecated SSE](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/)

### Anthropic Engineering Blog
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)

### Frontend
- [Vercel AI SDK v5 Blog](https://vercel.com/blog/ai-sdk-5) — UIMessage vs ModelMessage, custom transports
- [Vercel AI SDK v6 Blog](https://vercel.com/blog/ai-sdk-6) — per-tool strict mode
- [AI SDK Anthropic Provider](https://ai-sdk.dev/providers/ai-sdk-providers/anthropic) — thinking support, cache control

### SSE / Streaming
- [sse-starlette](https://github.com/sysid/sse-starlette) — production SSE for FastAPI
- [FastAPI + SSE + MCP Pattern](https://www.ragie.ai/blog/building-a-server-sent-events-sse-mcp-server-with-fastapi)

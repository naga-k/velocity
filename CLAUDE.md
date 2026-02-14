# Velocity — AI PM Agent

Agentic AI tool for startup PMs powered by Claude Opus 4.6. Connects to existing tools (Linear, Slack, Notion) and helps PMs make better product decisions by pulling together external signals and internal state. Built for the Anthropic hackathon (deadline: Feb 16, 2026).

## Current State

**Scaffold is complete and merged to `main`.** End-to-end chat works: message → FastAPI → Claude (Sonnet) → SSE → React UI. 40 backend tests pass, frontend builds clean. The agent layer currently uses the raw `anthropic` SDK — Track A replaces this with Claude Agent SDK.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, uv (package manager), anthropic SDK (scaffold) → Claude Agent SDK (Track A)
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Infrastructure:** Redis (session state/cache), SQLite (hackathon) / PostgreSQL (prod), Docker
- **AI Models:** Opus 4.6 (orchestrator + prioritization + doc agents), Sonnet 4.5 (scaffold chat + research + backlog agents)
- **Integrations:** MCP protocol — Linear, Slack, Web Search (stdio transport for hackathon)

## Project Structure

```
velocity/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point + CORS
│   │   ├── config.py            # Pydantic settings + env vars
│   │   ├── agent.py             # Agent layer — generate_response() interface
│   │   ├── sse_bridge.py        # (event_type, json_data) → ServerSentEvent
│   │   ├── models.py            # Pydantic request/response schemas + SSE contracts
│   │   └── routes/
│   │       ├── chat.py          # POST /api/chat → SSE stream
│   │       ├── sessions.py      # Session CRUD (in-memory for now)
│   │       └── health.py        # Health check
│   ├── tests/                   # pytest tests (40 passing)
│   │   ├── conftest.py          # Shared fixtures (async client, mock anthropic)
│   │   ├── test_chat.py         # SSE streaming tests
│   │   ├── test_models.py       # Pydantic model tests
│   │   ├── test_sessions.py     # Session CRUD tests
│   │   └── test_health.py       # Health endpoint tests
│   ├── memory/                  # Persistent product knowledge (file-based)
│   │   ├── product-context.md   # Product overview (loaded by agent)
│   │   ├── decisions/           # Decision log
│   │   └── insights/            # Synthesized insights
│   ├── pyproject.toml           # uv managed, [dependency-groups] dev for test deps
│   ├── uv.lock
│   └── Dockerfile
├── frontend/
│   ├── app/                     # Next.js App Router (page.tsx = chat UI)
│   ├── components/              # React components (chat/, ui/)
│   │   └── chat/                # ChatInput, ChatMessages, AgentActivityPanel
│   ├── hooks/
│   │   └── useChat.ts           # Fetch-based SSE parser + state management
│   ├── lib/
│   │   ├── api.ts               # API client (relative /api, proxied by Next.js)
│   │   └── types.ts             # TypeScript mirrors of backend Pydantic models
│   ├── package.json
│   └── next.config.ts           # API rewrite proxy → localhost:8000
├── docker-compose.yml           # Backend + Frontend + Redis
├── ARCHITECTURE.md              # Full system design (source of truth)
├── PRD.md                       # Product requirements
└── CLAUDE.md                    # This file
```

## Critical Interface

`generate_response()` in `agent.py` is the boundary between agent logic and everything else:

```python
async def generate_response(
    message: str, session_id: str, context: dict | None = None,
) -> AsyncGenerator[tuple[str, str], None]:
    """Yield (event_type, json_data) tuples for an SSE stream."""
```

Consumed by: `sse_bridge.py` → `routes/chat.py` → `EventSourceResponse` → frontend `useChat.ts`

### SSE Event Contract

| Event | Payload | Status |
|-------|---------|--------|
| `text` | `"bare string"` | Working |
| `thinking` | `{"text": "..."}` | Track A |
| `agent_activity` | `{"agent": "...", "status": "running\|completed", "task": "..."}` | Track A |
| `citation` | `{"type": "slack\|linear\|web", "url": "...", "title": "...", "snippet": "..."}` | Track A |
| `tool_call` | `{"tool": "...", "params": {...}}` | Track A |
| `error` | `{"message": "...", "recoverable": bool}` | Working |
| `done` | `{"tokens_used": {"input": N, "output": N}, "agents_used": [...]}` | Working |

## Commands

### Backend
```bash
cd backend
uv sync                                    # Install deps (test deps via [dependency-groups] dev)
uv run uvicorn app.main:app --reload --port 8000  # Run dev server
uv run pytest                              # Run tests (40 passing)
uv run pytest -x                           # Run tests, stop on first failure
uv add <package>                           # Add a dependency
```

### Frontend
```bash
cd frontend
npm install                             # Install dependencies
npm run dev                             # Run dev server (port 3000)
npm run build                           # Production build
npm run lint                            # Lint
```

### Docker (full stack)
```bash
docker compose up                       # Start all services
docker compose down                     # Stop all services
```

## Architecture Rules

**Read ARCHITECTURE.md for full details. These are the non-negotiable rules:**

1. **Claude Agent SDK IS the orchestrator.** Do NOT build a custom OrchestratorAgent class. Configure `ClaudeSDKClient` with system prompt, subagents (`AgentDefinition`), and MCP servers. The SDK handles the agent loop, tool execution, compaction, and streaming.

2. **FastAPI is a thin SSE bridge.** It receives HTTP requests, passes them to `ClaudeSDKClient`, and translates `StreamEvent` messages to SSE for the frontend. No business logic in routes.

3. **Subagents via AgentDefinition, not custom classes.** Define each agent (Research, Backlog, Prioritization, Doc) as an `AgentDefinition` with its own model, system prompt, and tools. The SDK invokes them via the `Task` tool.

4. **MCP for all integrations.** Use `McpStdioServerConfig` for hackathon (simplest). Linear, Slack, and Web Search connect via MCP servers. Custom PM tools use `@tool` decorator + `create_sdk_mcp_server()`.

5. **Three-tier memory.** Redis (working memory, TTL caches), SQLite (session history, configs), file-based markdown (product knowledge, decisions, insights). Just-in-time loading — don't dump everything into context.

6. **Ground truth at every step.** Every agent claim must cite a source (Slack message, Linear ticket, web result). No hallucinated metrics or ungrounded recommendations.

## Design Principles

- **P1: Context engineering over prompt engineering** — optimize token usage, just-in-time loading, aggressive compaction
- **P2: Simple, composable patterns first** — use workflow patterns (chaining, routing, parallelization, orchestrator-workers), add complexity only when simpler patterns fail
- **P3: Orchestrator-worker, not monolith** — lead agent coordinates, subagents handle focused tasks in isolated context windows
- **P4: Ground truth at every step** — agents cite sources, no hallucinations
- **P5: Build for demo, design for production** — must work reliably for demo, architecture should be extensible
- **P6: Showcase Opus 4.6 strengths** — 1M context, 128K output, deep reasoning, multi-agent orchestration

## Coding Conventions

### Python (backend)
- Pydantic models for all request/response schemas and config
- async/await everywhere — FastAPI routes, SDK calls, Redis operations
- Type hints on all function signatures
- snake_case for functions/variables, PascalCase for classes
- Keep route handlers thin — delegate to agent.py and sse_bridge.py

### TypeScript (frontend)
- Strict mode enabled
- React Server Components where possible, client components only when needed (interactivity, hooks)
- Custom hooks for all stateful logic (useChat, useAgentStream, useIntegrations)
- shadcn/ui for base components — don't build from scratch
- Tailwind for styling — no CSS modules or styled-components

### Testing
- Test-driven development — write tests alongside implementation
- Backend: pytest + pytest-asyncio + httpx (`AsyncClient` with `ASGITransport` for FastAPI)
- Frontend: vitest for component and hook tests
- Mock external services (Anthropic API, Redis, MCP) in tests — tests must run without API keys
- Run `uv run pytest` (backend) and `npm test` (frontend) before committing

### General
- No over-engineering — minimal abstractions, no premature generalization
- ARCHITECTURE.md is the source of truth for all design decisions
- No authentication for hackathon (single-user demo)
- `uv` for Python package management — no pip, no requirements.txt

## Key References

- [ARCHITECTURE.md](ARCHITECTURE.md) — Full system design, agent specs, data flows, deployment strategy
- [PRD.md](PRD.md) — Product requirements, user personas, feature areas, integration tiers
- [hackathon-resources.md](hackathon-resources.md) — Anthropic docs, SDK references, course links

## Environment Variables

```bash
ANTHROPIC_API_KEY=                     # Required
SLACK_BOT_TOKEN=                       # Required for Slack MCP
LINEAR_API_KEY=                        # Required for Linear MCP
REDIS_URL=redis://localhost:6379       # Default
DATABASE_URL=sqlite:///./data/app.db   # SQLite for hackathon
FRONTEND_URL=http://localhost:3000
```

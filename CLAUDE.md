# Velocity — AI PM Agent

Agentic AI tool for startup PMs powered by Claude Opus 4.6. Connects to existing tools (Linear, Slack) and helps PMs make better product decisions by pulling together external signals and internal state. Built for the Anthropic Build with Claude Hackathon (deadline: Feb 16, 2026).

## Current State

**Daytona sandbox integration is on `daytona-integration` branch.** End-to-end chat works: message → FastAPI → Daytona sandbox → Claude Agent SDK (Opus 4.6 orchestrator) → SSE → React UI. Four subagents (research, backlog, prioritization, doc-writer). Linear GraphQL tools (list, create, update with status changes). Slack MCP configured. Multi-turn conversation history preserved across messages. Using SDK fork for buffer deadlock fix.

**Recent fixes:**
- Linear `update_linear_issue` now supports status changes (resolves `state_name` → `stateId` via workflow states API)
- Linear `list_linear_issues` handles null GraphQL responses safely
- Slack MCP server pre-installed in Daytona sandbox (was failing because `npx` couldn't download at runtime)
- Non-JSON sandbox log lines no longer spam warnings (downgraded to debug level)

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, uv (package manager), Claude Agent SDK
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Sandboxes:** Daytona (ephemeral per-session sandbox execution)
- **Infrastructure:** Redis (session cache, optional), SQLite (hackathon), Docker
- **AI Models:** Opus 4.6 (orchestrator + prioritization + doc agents), Sonnet 4.5 (research + backlog agents)
- **Integrations:** MCP protocol — Linear (custom GraphQL tools), Slack (MCP stdio server)

## Project Structure

```
velocity/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point + CORS
│   │   ├── config.py                  # Pydantic settings + env vars
│   │   ├── agent.py                   # Agent layer — generate_response() interface
│   │   ├── daytona_manager.py         # Daytona sandbox lifecycle management
│   │   ├── sse_bridge.py              # (event_type, json_data) → ServerSentEvent
│   │   ├── models.py                  # Pydantic request/response schemas
│   │   ├── agents/
│   │   │   ├── sandbox_runner.py      # Runs INSIDE Daytona sandbox (SDK + tools)
│   │   │   ├── session_worker.py      # Manages sandbox per session, parses output
│   │   │   ├── orchestrator.py        # Local orchestrator (non-sandbox fallback)
│   │   │   ├── definitions.py         # AgentDefinition configs
│   │   │   ├── prompts/               # System prompts (orchestrator, research, etc.)
│   │   │   └── tools/                 # Custom PM tools (prioritization, docs, memory)
│   │   └── routes/
│   │       ├── chat.py                # POST /api/chat → SSE stream
│   │       ├── sessions.py            # Session CRUD
│   │       └── health.py              # Health check
│   ├── tests/                         # pytest tests (58 passing)
│   ├── memory/                        # Persistent product knowledge (file-based)
│   ├── pyproject.toml                 # uv managed
│   └── Dockerfile
├── frontend/
│   ├── app/                           # Next.js App Router (page.tsx = chat UI)
│   ├── components/
│   │   └── chat/                      # ChatInput, ChatMessages, AgentActivityPanel
│   ├── hooks/useChat.ts               # Fetch-based SSE parser + state management
│   ├── lib/
│   │   ├── api.ts                     # API client (proxied by Next.js)
│   │   └── types.ts                   # TypeScript mirrors of backend schemas
│   └── next.config.ts                 # API rewrite proxy → localhost:8000
├── docker-compose.yml
├── ARCHITECTURE.md                    # Full system design (source of truth)
├── PRD.md                             # Product requirements
└── CLAUDE.md                          # This file
```

## Critical Interfaces

### generate_response()

`agent.py` is the boundary between agent logic and everything else:

```python
async def generate_response(
    message: str, session_id: str, context: dict | None = None,
) -> AsyncGenerator[tuple[str, str], None]:
    """Yield (event_type, json_data) tuples for an SSE stream."""
```

Consumed by: `sse_bridge.py` → `routes/chat.py` → `EventSourceResponse` → frontend `useChat.ts`

### Sandbox Execution Flow

```
session_worker.py → daytona_manager.py (create sandbox) → upload sandbox_runner.py
  → execute command in sandbox → stream stdout (JSON lines) → parse → out_queue → SSE
```

The sandbox_runner.py is a self-contained script uploaded to each Daytona sandbox. It contains all agent definitions, tools, and the SDK execution loop. Output is JSON lines on stdout, logs on stderr.

### SSE Event Contract

| Event | Payload | Status |
|-------|---------|--------|
| `text` | `"bare string"` | Working |
| `thinking` | `{"text": "..."}` | Working |
| `agent_activity` | `{"agent": "...", "status": "running\|completed", "task": "..."}` | Working |
| `tool_call` | `{"tool": "...", "params": {...}}` | Working |
| `error` | `{"message": "...", "recoverable": bool}` | Working |
| `done` | `{"tokens_used": {"input": N, "output": N}, "agents_used": [...]}` | Working |

## Commands

### Backend
```bash
cd backend
uv sync                                    # Install deps
uv run uvicorn app.main:app --reload --port 8000  # Run dev server
uv run pytest                              # Run tests (58 passing)
uv run pytest -x                           # Stop on first failure
```

### Frontend
```bash
cd frontend
npm install
npm run dev                             # Dev server (port 3000)
npm run build                           # Production build
```

### Docker
```bash
docker compose up                       # Start all services
docker compose down                     # Stop
```

## Architecture Rules

1. **Claude Agent SDK IS the orchestrator.** No custom OrchestratorAgent class. Configure `ClaudeSDKClient` with system prompt, subagents, and MCP servers. The SDK handles the agent loop.

2. **FastAPI is a thin SSE bridge.** No business logic in routes.

3. **Subagents via AgentDefinition.** Research, Backlog, Prioritization, Doc Writer — each with its own model, prompt, and tools. SDK invokes via `Task` tool.

4. **MCP for all integrations.** Slack via MCP stdio server. Linear via custom `@tool` GraphQL functions + `create_sdk_mcp_server()`.

5. **Daytona sandboxes for isolation.** Each session gets an ephemeral sandbox. SDK runs inside it. Secrets passed as env vars or CLI args.

6. **Ground truth at every step.** Every claim must cite a source. No hallucinated metrics.

## Design Principles

- **P1: Context engineering over prompt engineering** — optimize token usage, just-in-time loading
- **P2: Simple, composable patterns first** — workflow patterns before frameworks
- **P3: Orchestrator-worker, not monolith** — subagents in isolated context windows
- **P4: Ground truth at every step** — cite sources, no hallucinations
- **P5: Build for demo, design for production** — reliable demo, extensible architecture
- **P6: Showcase Opus 4.6 strengths** — 1M context, deep reasoning, multi-agent orchestration

## Coding Conventions

### Python (backend)
- Pydantic models for all schemas and config
- async/await everywhere
- Type hints on all function signatures
- snake_case functions/variables, PascalCase classes
- Thin route handlers — delegate to agent.py and sse_bridge.py

### TypeScript (frontend)
- Strict mode, React Server Components where possible
- Custom hooks for stateful logic (useChat)
- shadcn/ui + Tailwind CSS

### Testing
- pytest + pytest-asyncio + httpx for backend
- Mock external services — tests run without API keys
- Test error paths, not just happy paths

### General
- No over-engineering
- ARCHITECTURE.md is source of truth
- `uv` for Python — no pip, no requirements.txt

## Environment Variables

```bash
ANTHROPIC_API_KEY=                     # Required
SLACK_BOT_TOKEN=                       # Required for Slack MCP
SLACK_TEAM_ID=                         # Slack workspace ID
LINEAR_API_KEY=                        # Required for Linear tools
DAYTONA_API_KEY=                       # Required for sandbox execution
DAYTONA_API_URL=https://app.daytona.io/api
DAYTONA_TARGET=us
REDIS_URL=redis://localhost:6379       # Optional, falls back to in-memory
DATABASE_URL=sqlite:///./data/app.db   # SQLite for hackathon
FRONTEND_URL=http://localhost:3000
```

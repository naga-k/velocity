# Velocity — AI PM Agent

Agentic AI tool for startup PMs powered by Claude Opus 4.6. Connects to existing tools (Linear, Slack, Notion) and helps PMs make better product decisions by pulling together external signals and internal state. Built for the Anthropic hackathon (deadline: Feb 16, 2026).

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, Claude Agent SDK
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Infrastructure:** Redis (session state/cache), SQLite (hackathon) / PostgreSQL (prod), Docker
- **AI Models:** Opus 4.6 (orchestrator + prioritization + doc agents), Sonnet 4.5 (research + backlog agents)
- **Integrations:** MCP protocol — Linear, Slack, Web Search (stdio transport for hackathon)

## Project Structure

```
velocity/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings + env vars
│   │   ├── agent.py             # Claude Agent SDK setup (orchestrator + subagents)
│   │   ├── sse_bridge.py        # StreamEvent → SSE translation
│   │   ├── models.py            # Pydantic request/response schemas
│   │   └── routes/
│   │       ├── chat.py          # POST /api/chat → SSE stream
│   │       ├── sessions.py      # Session CRUD
│   │       └── health.py        # Health check
│   ├── memory/                  # Persistent product knowledge (file-based)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # React components (chat/, sidebar/, ui/)
│   ├── hooks/                   # Custom hooks (useChat, useAgentStream)
│   ├── lib/                     # API client, types, utilities
│   ├── package.json
│   └── next.config.js
├── ARCHITECTURE.md              # Full system design (source of truth)
├── PRD.md                       # Product requirements
└── CLAUDE.md                    # This file
```

## Commands

### Backend
```bash
cd backend
pip install -r requirements.txt        # Install dependencies
uvicorn app.main:app --reload --port 8000  # Run dev server
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

### General
- No over-engineering — minimal abstractions, no premature generalization
- ARCHITECTURE.md is the source of truth for all design decisions
- No authentication for hackathon (single-user demo)
- Manual testing only — no test suite for hackathon scope

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

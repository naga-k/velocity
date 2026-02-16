# Velocity — AI PM Agent

An agentic AI product management assistant for startup PMs. Connects to your existing tools (Linear, Slack) and helps you make better product decisions by synthesizing external signals and internal state — so you spend less time gathering context and more time thinking.

Built with Claude Opus 4.6 and the Claude Agent SDK for the Anthropic Build with Claude Hackathon (Feb 2026).

## What It Does

**Ask Velocity anything a PM would ask their team:**

- "What should we prioritize this sprint?" — pulls Linear issues + Slack discussions, runs RICE scoring
- "Mark VEL-25 as done" — updates Linear tickets directly
- "Write a PRD for the new onboarding flow" — generates grounded documents citing real data
- "What are customers saying about search?" — searches Slack conversations for feedback patterns
- "Compare options A vs B" — applies weighted scoring frameworks with evidence

Velocity doesn't just chat — it **acts**. It reads and writes to your tools, cites sources for every claim, and coordinates specialized subagents to handle complex multi-step workflows.

## Architecture

```
User → Next.js UI → FastAPI (SSE bridge) → Claude Agent SDK (Opus 4.6)
                                                    │
                                          ┌─────────┼─────────┐
                                          │         │         │
                                     Research   Backlog   Prioritization
                                     (Sonnet)   (Sonnet)    (Opus)
                                          │         │         │
                                       Slack     Linear    RICE/ICE
                                       MCP       MCP       Scoring
```

- **Orchestrator** (Opus 4.6) — coordinates subagents, synthesizes results, maintains conversation
- **Research agent** (Sonnet 4.5) — searches Slack, web, and other sources for context
- **Backlog agent** (Sonnet 4.5) — reads/writes Linear issues, analyzes sprint state
- **Prioritization agent** (Opus 4.6) — applies RICE, impact-effort, weighted scoring
- **Doc Writer agent** (Opus 4.6) — generates PRDs, stakeholder updates, sprint summaries

All integrations use **MCP (Model Context Protocol)** — Linear and Slack connect via MCP stdio servers, custom PM tools use the SDK's `@tool` decorator.

Agent execution runs in **Daytona sandboxes** — each session gets an isolated environment with the Claude Agent SDK, streaming output back to the UI in real-time via SSE.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI | Claude Opus 4.6 (orchestrator), Sonnet 4.5 (subagents), Claude Agent SDK |
| Backend | Python 3.12, FastAPI, Daytona sandboxes |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Integrations | MCP protocol — Linear, Slack (stdio transport) |
| Infrastructure | Redis (cache), SQLite (sessions), Docker |

## Quick Start

### Prerequisites

- Python 3.12+, Node.js 18+, [uv](https://docs.astral.sh/uv/)
- API keys: `ANTHROPIC_API_KEY`, `LINEAR_API_KEY`, `SLACK_BOT_TOKEN`
- Daytona account for sandbox execution (`DAYTONA_API_KEY`)

### Setup

```bash
# Clone
git clone https://github.com/naga-k/velocity.git
cd velocity

# Backend
cd backend
cp .env.example .env  # Add your API keys
uv sync
uv run uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and start chatting.

### Docker

```bash
docker compose up
```

## Project Structure

```
velocity/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry + CORS
│   │   ├── config.py                  # Pydantic settings
│   │   ├── agent.py                   # generate_response() interface
│   │   ├── daytona_manager.py         # Sandbox lifecycle management
│   │   ├── sse_bridge.py              # Stream → SSE translation
│   │   ├── agents/
│   │   │   ├── sandbox_runner.py      # Runs inside Daytona sandbox
│   │   │   ├── session_worker.py      # Manages sandbox per session
│   │   │   ├── orchestrator.py        # Local orchestrator (non-sandbox)
│   │   │   ├── definitions.py         # Agent definitions
│   │   │   ├── prompts/               # System prompts (markdown)
│   │   │   └── tools/                 # Custom PM tools
│   │   └── routes/                    # API endpoints
│   └── tests/                         # pytest (58 tests)
├── frontend/
│   ├── app/                           # Next.js App Router
│   ├── components/chat/               # Chat UI components
│   ├── hooks/useChat.ts               # SSE streaming + state
│   └── lib/                           # API client + types
├── docker-compose.yml
├── ARCHITECTURE.md                    # Full system design
└── PRD.md                             # Product requirements
```

## Key Design Decisions

1. **Claude Agent SDK is the orchestrator** — no custom agent loop. The SDK handles tool execution, compaction, streaming, and subagent coordination.

2. **Daytona sandboxes for isolation** — each chat session runs the SDK in an ephemeral sandbox. Secrets stay server-side, execution is isolated.

3. **MCP for all integrations** — Linear reads/writes, Slack search, and custom PM tools all connect via MCP. Adding a new integration = adding a new MCP server config.

4. **Ground truth at every step** — every agent claim must cite a source (Linear ticket, Slack message, web result). The system prompt enforces this.

5. **Thin SSE bridge** — FastAPI does zero business logic. It passes messages to the SDK and translates stream events to SSE for the React frontend.

## Environment Variables

```bash
ANTHROPIC_API_KEY=          # Required — Claude API
SLACK_BOT_TOKEN=            # Required for Slack integration
SLACK_TEAM_ID=              # Slack workspace ID
LINEAR_API_KEY=             # Required for Linear integration
DAYTONA_API_KEY=            # Required for sandbox execution
DAYTONA_API_URL=            # Daytona API endpoint
REDIS_URL=                  # Optional (falls back to in-memory)
```

## License

MIT

# Velocity Project — Comprehensive Linear Backlog Report

**Generated:** 2026-02-14 (Fresh data from Linear API)
**Organization:** Velocity (velocitypm)
**User:** Naga Karumuri (anjaneyulun02@gmail.com)
**Project:** [Velocity — Built with Opus 4.6 Hackathon](https://linear.app/velocitypm/project/velocity-built-with-opus-46-hackathon-4b9c4cc41ebb)
**Project Progress:** 27.2% complete
**Deadline:** Feb 16, 2026 3:00 PM EST (hackathon submission)

---

## Executive Summary

### Overall Status
- **Total Issues:** 28 tickets
- **Active Sprint/Cycle:** None configured
- **All tickets unassigned** (single contributor project)

### Status Breakdown
| Status | Count | Percentage |
|--------|-------|------------|
| **Done** | 6 | 21.4% |
| **In Progress** | 1 | 3.6% |
| **Todo** | 20 | 71.4% |
| **Backlog** | 1 | 3.6% |

### Priority Distribution
| Priority | Count | Percentage |
|----------|-------|------------|
| **Urgent** | 9 | 32.1% |
| **High** | 7 | 25.0% |
| **Medium** | 2 | 7.1% |
| **No Priority** | 4 | 14.3% |
| **Backlog** | 6 | 21.4% |

### Track Distribution
- **Track A (Agent SDK + MCP):** 4 tickets — 3 Done, 1 In Progress (VEL-21 bug)
- **Track B (Frontend UI/UX):** 7 tickets — 0 Done, 7 Todo
- **Track C (Memory + Persistence):** 3 tickets — 3 Done (100%)
- **Track D (Deployment):** 5 tickets — 0 Done, 5 Todo
- **Integration Setup:** 2 tickets — 0 Done, 2 Todo
- **Bugs (cross-track):** 3 tickets — 0 Done, 1 In Progress, 2 Todo
- **Linear Onboarding:** 4 tickets — Not relevant to project (can be closed)

---

## Detailed Breakdown by Status

### 🟢 Done (6 tickets)

#### Track A — Agent SDK + MCP (3 Done)

**[VEL-5](https://linear.app/velocitypm/issue/VEL-5/integrate-claude-agent-sdk-as-orchestrator): Integrate Claude Agent SDK as orchestrator**
- **Priority:** Urgent
- **Labels:** `track-a`
- **Completed:** 2026-02-15
- **Description:** Replace scaffold Anthropic API with Claude Agent SDK. ClaudeSDKClient with Opus 4.6 orchestrator, 4 subagents (research, backlog, prioritization, doc-writer), bypassPermissions mode, adaptive thinking. 58 tests passing. Merged to main.

**[VEL-6](https://linear.app/velocitypm/issue/VEL-6/configure-slack-linear-mcp-servers): Configure Slack + Linear MCP servers**
- **Priority:** Urgent
- **Labels:** `track-a`, `integration`
- **Completed:** 2026-02-15
- **Description:** Wire MCP servers into ClaudeSDKClient options. Slack MCP via @modelcontextprotocol/server-slack (stdio), Linear MCP via mcp.linear.app (HTTP) or linear-mcp (stdio), conditional based on credentials, custom PM tools (read_product_context, save_insight). Config wired, needs real tokens to test E2E.

**[VEL-7](https://linear.app/velocitypm/issue/VEL-7/build-sse-streaming-bridge): Build SSE streaming bridge**
- **Priority:** Urgent
- **Labels:** `track-a`
- **Completed:** 2026-02-15
- **Description:** Three-layer bridge: routes/chat.py → agent.py → sse_bridge.py. Events: text, thinking, agent_activity, tool_call, error, done. Handles duplicate text suppression (StreamEvent deltas vs TextBlocks), guaranteed cleanup via try/finally + done_emitted flag. Working end-to-end.

#### Track C — Memory + Persistence (3 Done)

**[VEL-15](https://linear.app/velocitypm/issue/VEL-15/implement-sqlite-persistence-layer): Implement SQLite persistence layer**
- **Priority:** Urgent
- **Labels:** `track-c`
- **Completed:** 2026-02-15
- **Description:** SQLite via aiosqlite for session history. database.py: init_db(), get_db() context manager. Tables: sessions, messages with FK cascade delete, index on session_id. 7 database tests passing. E2E verified — sessions persist across restart.

**[VEL-16](https://linear.app/velocitypm/issue/VEL-16/implement-redis-working-memory): Implement Redis working memory**
- **Priority:** Urgent
- **Labels:** `track-c`
- **Completed:** 2026-02-15
- **Description:** Redis via redis.asyncio for cache and session state. cache_set/get with TTL (default 300s), set/get_session_state for working memory, graceful fallback (app runs without Redis). 8 Redis tests passing. E2E verified with real Docker Redis.

**[VEL-17](https://linear.app/velocitypm/issue/VEL-17/build-session-store-api): Build session store API**
- **Priority:** Urgent
- **Labels:** `track-c`
- **Completed:** 2026-02-15
- **Description:** Unified session API in session_store.py: create_session, get_session, list_sessions, delete_session, save_message, get_messages, get_session_context(session_id) → {messages, product_context, session_metadata}. 19 tests passing. PR #3 ready to merge. 95 total tests after rebase on main.

---

### 🟡 In Progress (1 ticket)

**[VEL-21](https://linear.app/velocitypm/issue/VEL-21/sdk-resume-broken-no-conversation-memory-between-turns): SDK resume broken — no conversation memory between turns**
- **Priority:** Urgent
- **Labels:** `Bug`, `track-a`
- **Assignee:** Unassigned
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Each message creates a fresh ClaudeSDKClient because SDK resume returns 0-token empty responses. This means every turn starts from scratch — the agent has no memory of previous messages in the session. Workaround: Fresh client per query, context lost between turns. Upstream: PR #572 submitted to claude-agent-sdk-python. Better workaround: Inject last N messages from session_store into system prompt (not implemented yet). **This is the biggest UX gap — users expect the agent to remember what they just said.**

---

### ⚪ Todo (20 tickets)

#### Track B — Frontend UI/UX (7 Todo)

**[VEL-8](https://linear.app/velocitypm/issue/VEL-8/add-markdown-rendering-in-chat-messages): Add markdown rendering in chat messages**
- **Priority:** Urgent
- **Labels:** `track-b`, `ux`
- **Created:** 2026-02-15
- **Description:** Agent responses include markdown (headers, lists, bold, code blocks, tables) but frontend renders as plain text. Use react-markdown + remark-gfm. Need syntax highlighting for code blocks too. **This is the single biggest UX improvement — responses look terrible without it.**

**[VEL-9](https://linear.app/velocitypm/issue/VEL-9/show-thinking-indicators-in-ui): Show thinking indicators in UI**
- **Priority:** High
- **Labels:** `track-b`, `ux`
- **Created:** 2026-02-15
- **Description:** Backend emits 'thinking' events with extended thinking text. Frontend receives them (useChat handles the event type) but doesn't render anything. Show a subtle collapsible section or animated indicator when the agent is reasoning. Important for complex multi-agent queries that take 15-30 seconds.

**[VEL-10](https://linear.app/velocitypm/issue/VEL-10/build-source-cards-for-citations): Build source cards for citations**
- **Priority:** High
- **Labels:** `track-b`, `ux`
- **Created:** 2026-02-15
- **Description:** When the agent cites a Slack message or Linear ticket, show an inline card: Slack (channel name, author, timestamp, message snippet), Linear (ticket ID, title, status, priority badge), Web (page title, URL, excerpt). CitationData type already defined in frontend/lib/types.ts. Backend needs to emit citation events. Frontend needs SourceCard component. Reference: Perplexity-style inline citations.

**[VEL-11](https://linear.app/velocitypm/issue/VEL-11/add-session-sidebar-with-history): Add session sidebar with history**
- **Priority:** High
- **Labels:** `track-b`, `Feature`
- **Created:** 2026-02-15
- **Description:** Currently every page load creates a new session (useMemo uuid). Need: Left sidebar with session list (GET /api/sessions), click to load previous session, new session button, session titles (auto-generated from first message). Track C persistence layer is ready — sessions persist in SQLite.

**[VEL-12](https://linear.app/velocitypm/issue/VEL-12/improve-agent-activity-display): Improve agent activity display**
- **Priority:** High
- **Labels:** `track-b`, `ux`
- **Created:** 2026-02-15
- **Description:** AgentActivityPanel shows badges but they're minimal. Improve to show: which subagent is running (research, backlog, prioritization, doc-writer), what it's doing (task description from the agent_activity event), progress/elapsed time, tool calls being made (Slack search, Linear query, etc.). Should feel like watching a team of PMs work in real-time.

**[VEL-13](https://linear.app/velocitypm/issue/VEL-13/add-suggested-prompts-on-empty-state): Add suggested prompts on empty state**
- **Priority:** Medium
- **Labels:** `track-b`, `ux`
- **Created:** 2026-02-15
- **Description:** Empty chat just says 'Ask about sprints, priorities, or backlog.' Replace with 3-4 clickable suggested prompts: 'What should we prioritize this sprint?', 'Summarize recent customer feedback', 'Write a sprint update for stakeholders', 'What are the blockers in our backlog?' Clicking sends the message directly.

**[VEL-14](https://linear.app/velocitypm/issue/VEL-14/add-integration-status-panel): Add integration status panel**
- **Priority:** Medium
- **Labels:** `track-b`, `Feature`
- **Created:** 2026-02-15
- **Description:** Sidebar panel showing which integrations are connected: Slack (green/red indicator), Linear (green/red indicator), Notion ('Coming soon' badge), Amplitude ('Coming soon' badge). Shows the agent has data sources. Makes the product feel complete even if not all integrations are wired.

#### Track D — Deployment (5 Todo)

**[VEL-18](https://linear.app/velocitypm/issue/VEL-18/deploy-backend-to-railway): Deploy backend to Railway**
- **Priority:** Urgent
- **Labels:** `track-d`
- **Created:** 2026-02-15
- **Description:** Deploy FastAPI backend to Railway. Dockerfile already exists. Need: env vars (ANTHROPIC_API_KEY, SLACK_BOT_TOKEN, LINEAR_API_KEY, REDIS_URL), persistent volume for SQLite data and memory/ files, health check at /api/health, CORS configured for Vercel frontend domain. Must support long-running agent requests (30-60s).

**[VEL-19](https://linear.app/velocitypm/issue/VEL-19/deploy-frontend-to-vercel): Deploy frontend to Vercel**
- **Priority:** Urgent
- **Labels:** `track-d`
- **Created:** 2026-02-15
- **Description:** Deploy Next.js frontend to Vercel. next.config.ts has API rewrite proxy → need to point to Railway backend URL. Environment: NEXT_PUBLIC_API_URL=https://velocity-backend.railway.app. Zero config otherwise — Vercel auto-detects Next.js. Test: full chat flow works on deployed stack.

**[VEL-20](https://linear.app/velocitypm/issue/VEL-20/set-up-upstash-redis): Set up Upstash Redis**
- **Priority:** High
- **Labels:** `track-d`
- **Created:** 2026-02-15
- **Description:** Managed Redis for cloud deployment. Upstash free tier: 10K commands/day, 256MB. Just change REDIS_URL env var — zero code changes. Already supported: config.py reads REDIS_URL from env. Alternative: Railway managed Redis addon.

**[VEL-26](https://linear.app/velocitypm/issue/VEL-26/record-3-minute-demo-video): Record 3-minute demo video**
- **Priority:** Urgent
- **Labels:** `track-d`
- **Created:** 2026-02-15
- **Description:** Hackathon submission requires a demo video. Demo script: 1) Show the product — chat UI, agent activity panel, 2) Ask 'What should we prioritize this sprint?' — show multi-agent orchestration, 3) Show cross-source synthesis (Slack discussions + Linear tickets + web research), 4) Ask for a sprint update doc — show doc-writer agent, 5) Show persistence — restart, sessions still there. Deadline: Feb 16, 3:00 PM EST.

**[VEL-27](https://linear.app/velocitypm/issue/VEL-27/write-hackathon-submission-100-200-words-readme): Write hackathon submission (100-200 words + README)**
- **Priority:** Urgent
- **Labels:** `track-d`
- **Created:** 2026-02-15
- **Description:** Submission requirements: 100-200 word summary, GitHub repo with README, working deployed app URL, demo video link. Key points to hit: Multi-agent orchestration with Opus 4.6, cross-source synthesis (Slack + Linear + web), 1M context window for full product context, persistent memory across sessions, dogfooding (we used Velocity to build Velocity).

#### Integration Setup (2 Todo)

**[VEL-24](https://linear.app/velocitypm/issue/VEL-24/set-up-slack-workspace-bot-for-demo): Set up Slack workspace + bot for demo**
- **Priority:** Urgent
- **Labels:** `integration`
- **Created:** 2026-02-15
- **Description:** Create Slack workspace and bot app for the hackathon demo. Steps: 1) Create workspace at slack.com/create, 2) Create app at api.slack.com/apps (Velocity PM Bot), 3) Scopes: channels:history, channels:read, chat:write, users:read, 4) Install to workspace, get xoxb- token + Team ID, 5) Run seed script: python scripts/seed_slack.py, 6) Add tokens to .env. Seed script creates #product, #engineering, #customer-feedback, #shipped, #general with realistic PM conversations about Velocity.

**[VEL-25](https://linear.app/velocitypm/issue/VEL-25/set-up-linear-workspace-for-demo): Set up Linear workspace for demo**
- **Priority:** Urgent
- **Labels:** `integration`
- **Created:** 2026-02-15
- **Description:** Create Linear workspace for the hackathon demo. Steps: 1) Create workspace at linear.app/new, 2) Settings → Account → Personal API Keys → Create (Full access), 3) Run seed script: python scripts/seed_linear.py, 4) Add LINEAR_API_KEY to .env. Seed script creates the full Velocity backlog — 20+ tickets across Track A-D with real descriptions, priorities, and labels.

#### Bugs (2 Todo)

**[VEL-22](https://linear.app/velocitypm/issue/VEL-22/mcp-package-names-in-agentpy-are-wrong): MCP package names in agent.py are wrong**
- **Priority:** Urgent
- **Labels:** `Bug`, `integration`
- **Created:** 2026-02-15
- **Description:** `@anthropic/slack-mcp` and `@anthropic/linear-mcp` don't exist on npm. Real packages: Slack: `@modelcontextprotocol/server-slack` (deprecated) or `slack-mcp-server`, Linear: `linear-mcp` (stdio) or `mcp.linear.app` (HTTP). Also missing: SLACK_TEAM_ID not in config.py — the Slack MCP requires it. Fix: Update agent.py _build_mcp_servers(), add slack_team_id to config.py.

**[VEL-23](https://linear.app/velocitypm/issue/VEL-23/sse-stream-drops-on-slow-agent-responses): SSE stream drops on slow agent responses**
- **Priority:** High
- **Labels:** `Bug`
- **Created:** 2026-02-15
- **Description:** When agent takes >30s (multi-subagent queries), SSE connection sometimes drops. Frontend shows error but agent may still be running server-side. Fix options: 1) Send SSE keepalive comments (`: keepalive\n\n`) every 15s, 2) Increase proxy/server timeout, 3) Both. Priority for demo — long queries are the most impressive ones.

#### Linear Onboarding (4 Todo — Can be closed)

**[VEL-1](https://linear.app/velocitypm/issue/VEL-1/get-familiar-with-linear): Get familiar with Linear**
- **Priority:** No priority
- **Labels:** None
- **Created:** 2026-02-14
- **Description:** Linear onboarding ticket. Not relevant to Velocity project. Can be closed.

**[VEL-2](https://linear.app/velocitypm/issue/VEL-2/set-up-your-teams): Set up your teams**
- **Priority:** No priority
- **Labels:** None
- **Created:** 2026-02-14
- **Description:** Linear onboarding ticket. Not relevant to Velocity project. Can be closed.

**[VEL-3](https://linear.app/velocitypm/issue/VEL-3/connect-your-tools): Connect your tools**
- **Priority:** No priority
- **Labels:** None
- **Created:** 2026-02-14
- **Description:** Linear onboarding ticket. Not relevant to Velocity project. Can be closed.

**[VEL-4](https://linear.app/velocitypm/issue/VEL-4/import-your-data): Import your data**
- **Priority:** No priority
- **Labels:** None
- **Created:** 2026-02-14
- **Description:** Linear onboarding ticket. Not relevant to Velocity project. Can be closed.

---

### ⚫ Backlog (1 ticket)

**[VEL-28](https://linear.app/velocitypm/issue/VEL-28/sdk-fix-or-upstream-claudesdkclient-cross-task-limitation): SDK: Fix or upstream ClaudeSDKClient cross-task limitation**
- **Priority:** High
- **Labels:** None
- **Created:** 2026-02-15
- **Description:** ClaudeSDKClient silently hangs when reused across ASGI request tasks (FastAPI). The SDK uses an anyio task group that can't deliver messages across asyncio task boundaries. Current Fix: Implemented `_SessionWorker` pattern — dedicated asyncio.Task per session with Queue bridges. Branch: `client-reuse`. PR pending. Upstream: Filed GitHub issue: https://github.com/anthropics/claude-agent-sdk-python/issues/576. The SDK docstring acknowledges this limitation but it's not in any official docs. Follow-up: Monitor upstream issue for SDK fix, if fixed upstream simplify worker pattern back to direct client reuse, consider contributing a PR with FastAPI example to their repo.

---

## Critical Blockers & Bugs

### High Priority Bugs (3 total)

1. **VEL-21 (In Progress)** — SDK resume broken, no conversation memory between turns
   - **Impact:** Critical UX gap, users can't have multi-turn conversations
   - **Workaround:** Fresh client per query (implemented)
   - **Better fix:** Inject last N messages from session_store into system prompt (not implemented)

2. **VEL-22 (Todo)** — MCP package names incorrect
   - **Impact:** Slack + Linear integrations won't work
   - **Status:** Code may already be fixed (check git status)

3. **VEL-23 (Todo)** — SSE stream drops on slow queries
   - **Impact:** Long multi-agent queries fail, poor demo experience
   - **Fix:** Add SSE keepalive comments every 15s

### Technical Debt (1 backlog)

4. **VEL-28 (Backlog)** — SDK cross-task limitation
   - **Impact:** Requires worker pattern workaround
   - **Status:** Upstream issue filed, workaround implemented on `client-reuse` branch

---

## Velocity Metrics

### Completion Statistics
- **Total completed:** 6 issues (21.4%)
- **All completed on:** 2026-02-15
- **Remaining work:** 22 active tickets (78.6%)

### Track-by-Track Progress

| Track | Total | Done | In Progress | Todo | Completion % |
|-------|-------|------|-------------|------|--------------|
| Track A (Agent SDK + MCP) | 4 | 3 | 1 | 0 | 75% |
| Track B (Frontend UI/UX) | 7 | 0 | 0 | 7 | 0% |
| Track C (Memory + Persistence) | 3 | 3 | 0 | 0 | 100% |
| Track D (Deployment) | 5 | 0 | 0 | 5 | 0% |
| Integration Setup | 2 | 0 | 0 | 2 | 0% |
| Bugs | 3 | 0 | 1 | 2 | 0% |

### Priority Burndown
- **Urgent remaining:** 9 tickets
- **High remaining:** 7 tickets
- **Medium remaining:** 2 tickets
- **Total high-priority remaining:** 18 tickets

### Estimated Time to Completion
Based on 9 urgent + 7 high priority tickets and typical task times:
- **Frontend (Track B):** ~4-6 hours
- **Deployment (Track D):** ~3-4 hours
- **Integration setup:** ~1-2 hours
- **Bug fixes:** ~2-3 hours
- **Total estimate:** ~10-15 hours of focused work

---

## Critical Path to Launch (Feb 16, 3:00 PM EST)

### Day 5 (Today) — Prioritized Sequence

#### Phase 1: Frontend Core (3-4 hours)
1. **VEL-8** — Markdown rendering (30 min) ⚡ HIGHEST IMPACT
2. **VEL-9** — Thinking indicators (45 min)
3. **VEL-11** — Session sidebar (90 min)

#### Phase 2: Bug Fixes (1-2 hours)
4. **VEL-22** — Fix MCP package names (30 min)
5. **VEL-23** — Add SSE keepalive (45 min)

#### Phase 3: Deployment (2-3 hours)
6. **VEL-18** — Deploy backend to Railway (60 min)
7. **VEL-19** — Deploy frontend to Vercel (30 min)
8. **VEL-20** — Set up Upstash Redis (30 min)

#### Phase 4: Demo & Submission (2-3 hours)
9. **VEL-26** — Record demo video (60 min)
10. **VEL-27** — Write submission (30 min)

### Items to Deprioritize (Nice-to-have)
- VEL-10 — Source cards for citations (defer)
- VEL-12 — Improved agent activity display (defer)
- VEL-13 — Suggested prompts (defer)
- VEL-14 — Integration status panel (defer)
- VEL-21 — SDK resume bug (workaround exists, upstream issue filed)
- VEL-24, VEL-25 — Integration setup (if already done, mark complete)
- VEL-1, VEL-2, VEL-3, VEL-4 — Linear onboarding (close/archive)

---

## Recommendations

### Immediate Actions (Next 1 hour)
1. **Close Linear onboarding tickets** (VEL-1, VEL-2, VEL-3, VEL-4) — not relevant
2. **Check if integrations are set up** — if VEL-24, VEL-25 are done, mark them complete
3. **Start VEL-8** (markdown rendering) — single biggest UX win
4. **Verify VEL-22 status** — git status shows agent.py is modified, may already be fixed

### Medium-term Actions (Next 4 hours)
1. **Complete Track B core** — VEL-8, VEL-9, VEL-11 (frontend polish)
2. **Fix critical bugs** — VEL-22, VEL-23 (integrations + stability)
3. **Deploy early** — VEL-18, VEL-19, VEL-20 (test prod environment)

### Pre-submission Actions (Next 8 hours)
1. **E2E testing** — Full flow on deployed stack
2. **Record demo** — VEL-26 (showcase multi-agent orchestration)
3. **Write submission** — VEL-27 (README + 100-200 word summary)
4. **Final polish** — Fix any critical bugs found during testing

### Risk Mitigation
- **No cycles configured:** Not critical for hackathon, skip
- **No estimates:** Use time-boxing instead (strict deadlines)
- **Single contributor:** Focus on MVP, defer nice-to-haves
- **71% in Todo:** Normal for final sprint, prioritize ruthlessly
- **No tests for frontend:** Skip for hackathon, manual testing only
- **Deadline pressure:** Cut scope aggressively, focus on demo quality

### Post-hackathon Backlog
- VEL-10, VEL-12, VEL-13, VEL-14 — Polish features
- VEL-21 — Better conversation memory (inject from session_store)
- VEL-28 — Monitor upstream SDK issue

---

## Project Health Indicators

### Strengths
- Track C (persistence) is 100% complete
- Track A (agent SDK) is 75% complete with solid foundation
- All completed work has test coverage
- Clear prioritization with track labels
- Good documentation in ticket descriptions

### Risks
- Track B (frontend) is 0% complete — biggest risk to demo quality
- Track D (deployment) is 0% complete — risk to submission deadline
- 3 critical bugs unresolved (VEL-21, VEL-22, VEL-23)
- Single contributor — no redundancy
- No active sprint/cycle — hard to track velocity
- All tickets unassigned — no accountability tracking

### Opportunities
- Markdown rendering (VEL-8) will dramatically improve UX
- Deployment is mostly config — should be quick
- Demo video can showcase impressive multi-agent orchestration
- Persistence layer (Track C) enables great demo of session history
- Integration setup (if already done) gives +2 tickets progress

---

*Report generated from Linear GraphQL API on 2026-02-14. All data is current as of generation time.*

# Velocity Project — Linear Backlog Analysis

**Generated:** 2026-02-14 22:14:08
**Organization:** Velocity
**User:** Naga Karumuri (anjaneyulun02@gmail.com)

---

## Executive Summary

- **Total Issues:** 28
- **Project:** [Velocity — Built with Opus 4.6 Hackathon](https://linear.app/velocitypm/project/velocity-built-with-opus-46-hackathon-4b9c4cc41ebb) (27.2% complete)
- **Active Sprint/Cycle:** None configured
- **Deadline:** Feb 16, 2026 3:00 PM EST (hackathon submission)

### Status Distribution
- **Done:** 6 issues (21.4%)
- **In Progress:** 1 issue (3.6%)
- **Todo:** 20 issues (71.4%)
- **Backlog:** 1 issue (3.6%)

### Priority Distribution
- **Urgent:** 15 issues (53.6%)
- **High:** 7 issues (25.0%)
- **Medium:** 2 issues (7.1%)
- **No priority:** 4 issues (14.3%)

### Track Distribution
- **Track A (Agent SDK + MCP):** 4 issues — 6 DONE, merged to main
- **Track B (Frontend UI/UX):** 7 issues — 0 done, current priority
- **Track C (Memory + Persistence):** 3 issues — 3 DONE, PR ready
- **Track D (Deployment):** 5 issues — 0 done, after Track B

### Critical Blockers
- **3 bug tickets** (all high/urgent priority)
- **VEL-21** (In Progress): SDK resume broken — no conversation memory
- **VEL-22** (Todo): MCP package names incorrect
- **VEL-23** (Todo): SSE stream drops on long queries

---

## Detailed Breakdown by Status

### 🟡 In Progress (1 issues)

#### [VEL-21](https://linear.app/velocitypm/issue/VEL-21/sdk-resume-broken-no-conversation-memory-between-turns): SDK resume broken — no conversation memory between turns
- **Priority:** Urgent
- **Labels:** `Bug`, `track-a`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Each message creates a fresh ClaudeSDKClient because SDK resume returns 0-token empty responses. This means every turn starts from scratch — the agent has no memory of previous messages in the session...


### ⚪ Todo (20 issues)

#### [VEL-14](https://linear.app/velocitypm/issue/VEL-14/add-integration-status-panel): Add integration status panel
- **Priority:** Medium
- **Labels:** `track-b`, `Feature`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Sidebar panel showing which integrations are connected:  * Slack: green/red indicator * Linear: green/red indicator * Notion: 'Coming soon' badge * Amplitude: 'Coming soon' badge  Shows the agent has ...

#### [VEL-13](https://linear.app/velocitypm/issue/VEL-13/add-suggested-prompts-on-empty-state): Add suggested prompts on empty state
- **Priority:** Medium
- **Labels:** `track-b`, `ux`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Empty chat just says 'Ask about sprints, priorities, or backlog.'  Replace with 3-4 clickable suggested prompts:  * 'What should we prioritize this sprint?' * 'Summarize recent customer feedback' * 'W...

#### [VEL-9](https://linear.app/velocitypm/issue/VEL-9/show-thinking-indicators-in-ui): Show thinking indicators in UI
- **Priority:** High
- **Labels:** `track-b`, `ux`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Backend emits 'thinking' events with extended thinking text. Frontend receives them (useChat handles the event type) but doesn't render anything.  Show a subtle collapsible section or animated indicat...

#### [VEL-23](https://linear.app/velocitypm/issue/VEL-23/sse-stream-drops-on-slow-agent-responses): SSE stream drops on slow agent responses
- **Priority:** High
- **Labels:** `Bug`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** When agent takes >30s (multi-subagent queries), SSE connection sometimes drops.  Frontend shows error but agent may still be running server-side.  **Fix options:**  1. Send SSE keepalive comments (`: ...

#### [VEL-20](https://linear.app/velocitypm/issue/VEL-20/set-up-upstash-redis): Set up Upstash Redis
- **Priority:** High
- **Labels:** `track-d`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Managed Redis for cloud deployment.  * Upstash free tier: 10K commands/day, 256MB * Just change REDIS_URL env var — zero code changes * Already supported: [config.py](<http://config.py>) reads REDIS_U...

#### [VEL-12](https://linear.app/velocitypm/issue/VEL-12/improve-agent-activity-display): Improve agent activity display
- **Priority:** High
- **Labels:** `track-b`, `ux`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** AgentActivityPanel shows badges but they're minimal. Improve to show:  * Which subagent is running (research, backlog, prioritization, doc-writer) * What it's doing (task description from the agent_ac...

#### [VEL-11](https://linear.app/velocitypm/issue/VEL-11/add-session-sidebar-with-history): Add session sidebar with history
- **Priority:** High
- **Labels:** `track-b`, `Feature`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Currently every page load creates a new session (useMemo uuid). Need:  * Left sidebar with session list (GET /api/sessions) * Click to load previous session * New session button * Session titles (auto...

#### [VEL-10](https://linear.app/velocitypm/issue/VEL-10/build-source-cards-for-citations): Build source cards for citations
- **Priority:** High
- **Labels:** `track-b`, `ux`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** When the agent cites a Slack message or Linear ticket, show an inline card:  * Slack: channel name, author, timestamp, message snippet * Linear: ticket ID, title, status, priority badge * Web: page ti...

#### [VEL-8](https://linear.app/velocitypm/issue/VEL-8/add-markdown-rendering-in-chat-messages): Add markdown rendering in chat messages
- **Priority:** Urgent
- **Labels:** `track-b`, `ux`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Agent responses include markdown (headers, lists, bold, code blocks, tables) but frontend renders as plain text.  Use react-markdown + remark-gfm. Need syntax highlighting for code blocks too.  This i...

#### [VEL-27](https://linear.app/velocitypm/issue/VEL-27/write-hackathon-submission-100-200-words-readme): Write hackathon submission (100-200 words + README)
- **Priority:** Urgent
- **Labels:** `track-d`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Submission requirements:  * 100-200 word summary * GitHub repo with README * Working deployed app URL * Demo video link  Key points to hit:  * Multi-agent orchestration with Opus 4.6 * Cross-source sy...

#### [VEL-26](https://linear.app/velocitypm/issue/VEL-26/record-3-minute-demo-video): Record 3-minute demo video
- **Priority:** Urgent
- **Labels:** `track-d`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Hackathon submission requires a demo video.  Demo script:  1. Show the product — chat UI, agent activity panel 2. Ask 'What should we prioritize this sprint?' — show multi-agent orchestration 3. Show ...

#### [VEL-25](https://linear.app/velocitypm/issue/VEL-25/set-up-linear-workspace-for-demo): Set up Linear workspace for demo
- **Priority:** Urgent
- **Labels:** `integration`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Create Linear workspace for the hackathon demo.  1. Create workspace at linear.app/new 2. Settings → Account → Personal API Keys → Create (Full access) 3. Run seed script: python scripts/seed_linear.p...

#### [VEL-24](https://linear.app/velocitypm/issue/VEL-24/set-up-slack-workspace-bot-for-demo): Set up Slack workspace + bot for demo
- **Priority:** Urgent
- **Labels:** `integration`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Create Slack workspace and bot app for the hackathon demo.  1. Create workspace at [slack.com/create](<http://slack.com/create>) 2. Create app at [api.slack.com/apps](<http://api.slack.com/apps>) (Vel...

#### [VEL-22](https://linear.app/velocitypm/issue/VEL-22/mcp-package-names-in-agentpy-are-wrong): MCP package names in agent.py are wrong
- **Priority:** Urgent
- **Labels:** `Bug`, `integration`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** `@anthropic/slack-mcp` and `@anthropic/linear-mcp` don't exist on npm.  Real packages:  * Slack: `@modelcontextprotocol/server-slack` (deprecated) or `slack-mcp-server` * Linear: `linear-mcp` (stdio) ...

#### [VEL-19](https://linear.app/velocitypm/issue/VEL-19/deploy-frontend-to-vercel): Deploy frontend to Vercel
- **Priority:** Urgent
- **Labels:** `track-d`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Deploy Next.js frontend to Vercel.  * next.config.ts has API rewrite proxy → need to point to Railway backend URL * Environment: NEXT_PUBLIC_API_URL=[https://velocity-backend.railway.app](<https://vel...

#### [VEL-18](https://linear.app/velocitypm/issue/VEL-18/deploy-backend-to-railway): Deploy backend to Railway
- **Priority:** Urgent
- **Labels:** `track-d`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** Deploy FastAPI backend to Railway.  * Dockerfile already exists * Need: env vars (ANTHROPIC_API_KEY, SLACK_BOT_TOKEN, LINEAR_API_KEY, REDIS_URL) * Persistent volume for SQLite data and memory/ files *...

#### [VEL-4](https://linear.app/velocitypm/issue/VEL-4/import-your-data): Import your data
- **Priority:** No priority
- **Labels:** *none*
- **Assignee:** *Unassigned*
- **Created:** 2026-02-14 | **Updated:** 2026-02-14
- **Description:** Sync data between Linear and your other tools.  ![import-your-data.png](https://uploads.linear.app/fe63b3e2-bf87-46c0-8784-cd7d639287c8/80d7e050-dd1f-4d4f-8257-b29c16087017/65c16454-30f3-4f4a-8f25-c24...

#### [VEL-3](https://linear.app/velocitypm/issue/VEL-3/connect-your-tools): Connect your tools
- **Priority:** No priority
- **Labels:** *none*
- **Assignee:** *Unassigned*
- **Created:** 2026-02-14 | **Updated:** 2026-02-14
- **Description:** Integrations turn Linear into your source of truth around product development. Keep data in sync, and eliminate manual updates between tools.  ![connect-your-tools.png](https://uploads.linear.app/fe63...

#### [VEL-2](https://linear.app/velocitypm/issue/VEL-2/set-up-your-teams): Set up your teams
- **Priority:** No priority
- **Labels:** *none*
- **Assignee:** *Unassigned*
- **Created:** 2026-02-14 | **Updated:** 2026-02-14
- **Description:** This workspace is a container for your organization’s work.   * [Learn more about Workspaces](<https://linear.app/docs/workspaces>)   How to configure settings and workflows   Teams are how you organi...

#### [VEL-1](https://linear.app/velocitypm/issue/VEL-1/get-familiar-with-linear): Get familiar with Linear
- **Priority:** No priority
- **Labels:** *none*
- **Assignee:** *Unassigned*
- **Created:** 2026-02-14 | **Updated:** 2026-02-14
- **Description:** Welcome to Linear!   Watch an introductory video and access a list of resources below.  [LinearH264Version_1.mp4](https://uploads.linear.app/fe63b3e2-bf87-46c0-8784-cd7d639287c8/a044fb03-9b84-470c-ab6...


### 🟢 Done (6 issues)

#### [VEL-7](https://linear.app/velocitypm/issue/VEL-7/build-sse-streaming-bridge): Build SSE streaming bridge
- **Priority:** Urgent
- **Labels:** `track-a`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Completed:** 2026-02-15
- **Description:** Three-layer bridge: routes/chat.py → [agent.py](<http://agent.py>) → sse_bridge.py  Events: text, thinking, agent_activity, tool_call, error, done Handles duplicate text suppression (StreamEvent delta...

#### [VEL-6](https://linear.app/velocitypm/issue/VEL-6/configure-slack-linear-mcp-servers): Configure Slack + Linear MCP servers
- **Priority:** Urgent
- **Labels:** `track-a`, `integration`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Completed:** 2026-02-15
- **Description:** Wire MCP servers into ClaudeSDKClient options.  * Slack MCP via @modelcontextprotocol/server-slack (stdio) * Linear MCP via mcp.linear.app (HTTP) or linear-mcp (stdio) * Conditional: only added when c...

#### [VEL-5](https://linear.app/velocitypm/issue/VEL-5/integrate-claude-agent-sdk-as-orchestrator): Integrate Claude Agent SDK as orchestrator
- **Priority:** Urgent
- **Labels:** `track-a`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Completed:** 2026-02-15
- **Description:** Replace scaffold Anthropic API with Claude Agent SDK.  * ClaudeSDKClient with Opus 4.6 orchestrator * 4 subagents: research, backlog, prioritization, doc-writer * bypassPermissions mode for hackathon ...

#### [VEL-17](https://linear.app/velocitypm/issue/VEL-17/build-session-store-api): Build session store API
- **Priority:** Urgent
- **Labels:** `track-c`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Completed:** 2026-02-15
- **Description:** Unified session API in session_store.py:  * create_session, get_session, list_sessions, delete_session * save_message, get_messages * get_session_context(session_id) → {messages, product_context, sess...

#### [VEL-16](https://linear.app/velocitypm/issue/VEL-16/implement-redis-working-memory): Implement Redis working memory
- **Priority:** Urgent
- **Labels:** `track-c`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Completed:** 2026-02-15
- **Description:** Redis via redis.asyncio for cache and session state.  * cache_set/get with TTL (default 300s) * set/get_session_state for working memory * Graceful fallback: app runs without Redis (warning, not error...

#### [VEL-15](https://linear.app/velocitypm/issue/VEL-15/implement-sqlite-persistence-layer): Implement SQLite persistence layer
- **Priority:** Urgent
- **Labels:** `track-c`
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Completed:** 2026-02-15
- **Description:** SQLite via aiosqlite for session history.  * [database.py](<http://database.py>): init_db(), get_db() context manager * Tables: sessions (id, title, created_at, updated_at), messages (id, session_id, ...


### ⚫ Backlog (1 issues)

#### [VEL-28](https://linear.app/velocitypm/issue/VEL-28/sdk-fix-or-upstream-claudesdkclient-cross-task-limitation): SDK: Fix or upstream ClaudeSDKClient cross-task limitation
- **Priority:** High
- **Labels:** *none*
- **Assignee:** *Unassigned*
- **Created:** 2026-02-15 | **Updated:** 2026-02-15
- **Description:** ## Context  ClaudeSDKClient silently hangs when reused across ASGI request tasks (FastAPI). The SDK uses an anyio task group that cant deliver messages across asyncio task boundaries.  ## Current Fix ...


---

## Velocity Metrics

### Completed Work
- **Total completed:** 6 issues
- **Completion rate:** 21.4%
- **All completed on:** 2026-02-15

### Track Progress
- **Track A:** 4 issues completed (100% — merged to main)
- **Track B:** 0/7 issues completed (0% — current focus)
- **Track C:** 3 issues completed (100% — PR #3 ready)
- **Track D:** 0/5 issues completed (0% — after Track B)

### Burndown
- **Remaining urgent:** 9
- **Remaining high:** 7
- **Est. remaining work:** ~16-20 hours (based on 15 urgent + 7 high priority items)

---

## Critical Path to Launch

### Day 5 (Today) — Frontend + Deploy
1. **VEL-8** — Markdown rendering (30 min)
2. **VEL-9** — Thinking indicators (45 min)
3. **VEL-11** — Session sidebar (90 min)
4. **VEL-18** — Deploy backend to Railway (60 min)
5. **VEL-19** — Deploy frontend to Vercel (30 min)
6. **VEL-26** — Record demo video (60 min)
7. **VEL-27** — Write submission (30 min)

### Blockers to Resolve
- **VEL-21** — SDK resume bug (workaround exists, need proper fix)
- **VEL-22** — Fix MCP package names (already fixed in code per git status)
- **VEL-23** — SSE keepalive for long queries

---

## Recommendations

### Immediate Actions
1. **Merge Track C PR #3** — persistence layer is ready, all tests pass
2. **Focus on Track B frontend** — biggest UX impact for demo
3. **Fix VEL-22** — MCP integration critical for demo
4. **Deploy early** — test prod environment before final submission

### De-prioritize
- VEL-1, VEL-2, VEL-3, VEL-4 — Linear onboarding tickets (not relevant)
- VEL-28 — SDK upstream issue (track long-term, not blocking)
- VEL-14 — Integration status panel (nice-to-have)
- VEL-13 — Suggested prompts (nice-to-have)

### Risk Mitigation
- **No cycles configured:** Consider creating a "Hackathon Sprint" cycle for velocity tracking
- **No estimates:** Hard to gauge completion time without story points
- **Single contributor:** All work unassigned, high bus factor
- **71% in Todo:** Large batch of unstarted work with <24h to deadline

---

*Report generated from Linear workspace at 2026-02-14 22:14:08*

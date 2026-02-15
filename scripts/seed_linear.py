#!/usr/bin/env python3
"""Seed a Linear workspace with Velocity project data.

Usage:
    LINEAR_API_KEY=lin_api_xxx python scripts/seed_linear.py

Creates the actual Velocity hackathon backlog — tracks, features, bugs,
and tech debt from the real project. This is dogfooding: using Velocity
to manage Velocity.
"""

import json
import os
import sys
import urllib.request

API_KEY = os.environ.get("LINEAR_API_KEY", "")
if not API_KEY:
    print("ERROR: Set LINEAR_API_KEY environment variable")
    sys.exit(1)

ENDPOINT = "https://api.linear.app/graphql"


def gql(query: str, variables: dict | None = None, allow_errors: bool = False) -> dict:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Authorization": API_KEY,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if "errors" in result and not allow_errors:
        print(f"GraphQL error: {result['errors']}")
        sys.exit(1)
    return result.get("data") or {}


# --- Get workspace info ---
print("Fetching workspace info...")
data = gql("{ teams { nodes { id name } } }")
teams = data["teams"]["nodes"]
if not teams:
    print("No teams found. Create a team in Linear first.")
    sys.exit(1)

team = teams[0]
team_id = team["id"]
print(f"Using team: {team['name']} ({team_id})")

# --- Get workflow states via team ---
states_data = gql(
    """
    query($teamId: String!) {
        team(id: $teamId) {
            states { nodes { id name type } }
        }
    }
    """,
    {"teamId": team_id},
)
states = {}
for s in states_data["team"]["states"]["nodes"]:
    states[s["type"]] = s["id"]
    states[s["name"].lower()] = s["id"]

print(f"  States: {list(states.keys())}")

# --- Create labels ---
print("Creating labels...")
LABELS = {
    "track-a": "#4CAF50",    # Agent SDK — green (done)
    "track-b": "#2196F3",    # Frontend — blue
    "track-c": "#9C27B0",    # Persistence — purple (done)
    "track-d": "#FF9800",    # Deployment — orange
    "bug": "#F44336",        # red
    "tech-debt": "#607D8B",  # grey
    "feature": "#00BCD4",    # cyan
    "ux": "#E91E63",         # pink
    "integration": "#795548", # brown
}
label_ids = {}

# First, fetch existing labels so we can reuse them
existing_labels_data = gql("""{ issueLabels { nodes { id name } } }""")
existing_labels = {l["name"].lower(): l["id"] for l in existing_labels_data.get("issueLabels", {}).get("nodes", [])}

for label_name, color in LABELS.items():
    # Check if label already exists (case-insensitive)
    if label_name.lower() in existing_labels:
        label_ids[label_name] = existing_labels[label_name.lower()]
        print(f"  Using existing label: {label_name}")
        continue
    result = gql(
        """
        mutation($input: IssueLabelCreateInput!) {
            issueLabelCreate(input: $input) {
                issueLabel { id name }
                success
            }
        }
        """,
        {"input": {"name": label_name, "teamId": team_id, "color": color}},
        allow_errors=True,
    )
    created = result.get("issueLabelCreate", {}).get("issueLabel")
    if created:
        label_ids[label_name] = created["id"]
        print(f"  Created label: {label_name}")
    else:
        print(f"  Skipped label: {label_name} (may already exist)")

# --- Create project ---
print("Creating project...")
try:
    result = gql(
        """
        mutation($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                project { id name }
                success
            }
        }
        """,
        {"input": {"name": "Velocity — Built with Opus 4.6 Hackathon", "teamIds": [team_id]}},
    )
    project_id = result["projectCreate"]["project"]["id"]
    print(f"  Created project: Velocity ({project_id})")
except Exception as e:
    print(f"  Project creation issue: {e}")
    project_id = None

# --- Create tickets ---
print("Creating tickets...")

TICKETS = [
    # =========================================================================
    # TRACK A — Agent SDK + MCP (DONE)
    # =========================================================================
    {"title": "Integrate Claude Agent SDK as orchestrator", "priority": 1,
     "labels": ["track-a"], "state": "done",
     "description": "Replace scaffold Anthropic API with Claude Agent SDK.\n\n"
     "- ClaudeSDKClient with Opus 4.6 orchestrator\n"
     "- 4 subagents: research, backlog, prioritization, doc-writer\n"
     "- bypassPermissions mode for hackathon\n"
     "- Adaptive thinking (ThinkingConfigAdaptive)\n\n"
     "**Done:** 58 tests passing. Merged to main."},

    {"title": "Configure Slack + Linear MCP servers", "priority": 1,
     "labels": ["track-a", "integration"], "state": "done",
     "description": "Wire MCP servers into ClaudeSDKClient options.\n\n"
     "- Slack MCP via @modelcontextprotocol/server-slack (stdio)\n"
     "- Linear MCP via mcp.linear.app (HTTP) or linear-mcp (stdio)\n"
     "- Conditional: only added when credentials are present\n"
     "- Custom PM tools: read_product_context, save_insight\n\n"
     "**Done:** Config wired. Needs real tokens to test E2E."},

    {"title": "Build SSE streaming bridge", "priority": 1,
     "labels": ["track-a"], "state": "done",
     "description": "Three-layer bridge: routes/chat.py → agent.py → sse_bridge.py\n\n"
     "Events: text, thinking, agent_activity, tool_call, error, done\n"
     "Handles duplicate text suppression (StreamEvent deltas vs TextBlocks).\n"
     "Guaranteed cleanup via try/finally + done_emitted flag.\n\n"
     "**Done:** Working end-to-end."},

    # =========================================================================
    # TRACK B — Frontend UI/UX (TODO — today's priority)
    # =========================================================================
    {"title": "Add markdown rendering in chat messages", "priority": 1,
     "labels": ["track-b", "ux"], "state": "unstarted",
     "description": "Agent responses include markdown (headers, lists, bold, code blocks, tables) "
     "but frontend renders as plain text.\n\n"
     "Use react-markdown + remark-gfm. Need syntax highlighting for code blocks too.\n\n"
     "This is the single biggest UX improvement — responses look terrible without it."},

    {"title": "Show thinking indicators in UI", "priority": 2,
     "labels": ["track-b", "ux"], "state": "unstarted",
     "description": "Backend emits 'thinking' events with extended thinking text. "
     "Frontend receives them (useChat handles the event type) but doesn't render anything.\n\n"
     "Show a subtle collapsible section or animated indicator when the agent is reasoning. "
     "Important for complex multi-agent queries that take 15-30 seconds."},

    {"title": "Build source cards for citations", "priority": 2,
     "labels": ["track-b", "ux"], "state": "unstarted",
     "description": "When the agent cites a Slack message or Linear ticket, show an inline card:\n\n"
     "- Slack: channel name, author, timestamp, message snippet\n"
     "- Linear: ticket ID, title, status, priority badge\n"
     "- Web: page title, URL, excerpt\n\n"
     "CitationData type already defined in frontend/lib/types.ts. "
     "Backend needs to emit citation events. Frontend needs SourceCard component.\n\n"
     "Reference: Perplexity-style inline citations."},

    {"title": "Add session sidebar with history", "priority": 2,
     "labels": ["track-b", "feature"], "state": "unstarted",
     "description": "Currently every page load creates a new session (useMemo uuid). Need:\n\n"
     "- Left sidebar with session list (GET /api/sessions)\n"
     "- Click to load previous session\n"
     "- New session button\n"
     "- Session titles (auto-generated from first message)\n\n"
     "Track C persistence layer is ready — sessions persist in SQLite."},

    {"title": "Improve agent activity display", "priority": 2,
     "labels": ["track-b", "ux"], "state": "unstarted",
     "description": "AgentActivityPanel shows badges but they're minimal. Improve to show:\n\n"
     "- Which subagent is running (research, backlog, prioritization, doc-writer)\n"
     "- What it's doing (task description from the agent_activity event)\n"
     "- Progress/elapsed time\n"
     "- Tool calls being made (Slack search, Linear query, etc.)\n\n"
     "Should feel like watching a team of PMs work in real-time."},

    {"title": "Add suggested prompts on empty state", "priority": 3,
     "labels": ["track-b", "ux"], "state": "unstarted",
     "description": "Empty chat just says 'Ask about sprints, priorities, or backlog.'\n\n"
     "Replace with 3-4 clickable suggested prompts:\n"
     "- 'What should we prioritize this sprint?'\n"
     "- 'Summarize recent customer feedback'\n"
     "- 'Write a sprint update for stakeholders'\n"
     "- 'What are the blockers in our backlog?'\n\n"
     "Clicking sends the message directly."},

    {"title": "Add integration status panel", "priority": 3,
     "labels": ["track-b", "feature"], "state": "unstarted",
     "description": "Sidebar panel showing which integrations are connected:\n\n"
     "- Slack: green/red indicator\n"
     "- Linear: green/red indicator\n"
     "- Notion: 'Coming soon' badge\n"
     "- Amplitude: 'Coming soon' badge\n\n"
     "Shows the agent has data sources. Makes the product feel complete even if "
     "not all integrations are wired."},

    # =========================================================================
    # TRACK C — Memory + Persistence (DONE)
    # =========================================================================
    {"title": "Implement SQLite persistence layer", "priority": 1,
     "labels": ["track-c"], "state": "done",
     "description": "SQLite via aiosqlite for session history.\n\n"
     "- database.py: init_db(), get_db() context manager\n"
     "- Tables: sessions (id, title, created_at, updated_at), "
     "messages (id, session_id, role, content, created_at)\n"
     "- FK cascade delete, index on session_id\n\n"
     "**Done:** 7 database tests passing. E2E verified — sessions persist across restart."},

    {"title": "Implement Redis working memory", "priority": 1,
     "labels": ["track-c"], "state": "done",
     "description": "Redis via redis.asyncio for cache and session state.\n\n"
     "- cache_set/get with TTL (default 300s)\n"
     "- set/get_session_state for working memory\n"
     "- Graceful fallback: app runs without Redis (warning, not error)\n\n"
     "**Done:** 8 Redis tests passing. E2E verified with real Docker Redis."},

    {"title": "Build session store API", "priority": 1,
     "labels": ["track-c"], "state": "done",
     "description": "Unified session API in session_store.py:\n\n"
     "- create_session, get_session, list_sessions, delete_session\n"
     "- save_message, get_messages\n"
     "- get_session_context(session_id) → {messages, product_context, session_metadata}\n\n"
     "**Done:** 19 tests passing. PR #3 ready to merge. 95 total tests after rebase on main."},

    # =========================================================================
    # TRACK D — Deployment (TODO)
    # =========================================================================
    {"title": "Deploy backend to Railway", "priority": 1,
     "labels": ["track-d"], "state": "unstarted",
     "description": "Deploy FastAPI backend to Railway.\n\n"
     "- Dockerfile already exists\n"
     "- Need: env vars (ANTHROPIC_API_KEY, SLACK_BOT_TOKEN, LINEAR_API_KEY, REDIS_URL)\n"
     "- Persistent volume for SQLite data and memory/ files\n"
     "- Health check at /api/health\n"
     "- CORS configured for Vercel frontend domain\n\n"
     "Must support long-running agent requests (30-60s)."},

    {"title": "Deploy frontend to Vercel", "priority": 1,
     "labels": ["track-d"], "state": "unstarted",
     "description": "Deploy Next.js frontend to Vercel.\n\n"
     "- next.config.ts has API rewrite proxy → need to point to Railway backend URL\n"
     "- Environment: NEXT_PUBLIC_API_URL=https://velocity-backend.railway.app\n"
     "- Zero config otherwise — Vercel auto-detects Next.js\n\n"
     "Test: full chat flow works on deployed stack."},

    {"title": "Set up Upstash Redis", "priority": 2,
     "labels": ["track-d"], "state": "unstarted",
     "description": "Managed Redis for cloud deployment.\n\n"
     "- Upstash free tier: 10K commands/day, 256MB\n"
     "- Just change REDIS_URL env var — zero code changes\n"
     "- Already supported: config.py reads REDIS_URL from env\n\n"
     "Alternative: Railway managed Redis addon."},

    # =========================================================================
    # BUGS — Known issues
    # =========================================================================
    {"title": "SDK resume broken — no conversation memory between turns", "priority": 1,
     "labels": ["bug", "track-a"], "state": "started",
     "description": "Each message creates a fresh ClaudeSDKClient because SDK resume returns "
     "0-token empty responses. This means every turn starts from scratch — the agent has "
     "no memory of previous messages in the session.\n\n"
     "**Workaround:** Fresh client per query. Context lost between turns.\n"
     "**Upstream:** PR #572 submitted to claude-agent-sdk-python.\n"
     "**Better workaround:** Inject last N messages from session_store into system prompt. "
     "Not implemented yet.\n\n"
     "This is the biggest UX gap — users expect the agent to remember what they just said."},

    {"title": "MCP package names in agent.py are wrong", "priority": 1,
     "labels": ["bug", "integration"], "state": "unstarted",
     "description": "`@anthropic/slack-mcp` and `@anthropic/linear-mcp` don't exist on npm.\n\n"
     "Real packages:\n"
     "- Slack: `@modelcontextprotocol/server-slack` (deprecated) or `slack-mcp-server`\n"
     "- Linear: `linear-mcp` (stdio) or `mcp.linear.app` (HTTP)\n\n"
     "Also missing: SLACK_TEAM_ID not in config.py — the Slack MCP requires it.\n\n"
     "**Fix:** Update agent.py _build_mcp_servers(), add slack_team_id to config.py."},

    {"title": "SSE stream drops on slow agent responses", "priority": 2,
     "labels": ["bug"], "state": "unstarted",
     "description": "When agent takes >30s (multi-subagent queries), SSE connection sometimes drops.\n\n"
     "Frontend shows error but agent may still be running server-side.\n\n"
     "**Fix options:**\n"
     "1. Send SSE keepalive comments (`: keepalive\\n\\n`) every 15s\n"
     "2. Increase proxy/server timeout\n"
     "3. Both\n\n"
     "Priority for demo — long queries are the most impressive ones."},

    # =========================================================================
    # Integration setup
    # =========================================================================
    {"title": "Set up Slack workspace + bot for demo", "priority": 1,
     "labels": ["integration"], "state": "unstarted",
     "description": "Create Slack workspace and bot app for the hackathon demo.\n\n"
     "1. Create workspace at slack.com/create\n"
     "2. Create app at api.slack.com/apps (Velocity PM Bot)\n"
     "3. Scopes: channels:history, channels:read, chat:write, users:read\n"
     "4. Install to workspace, get xoxb- token + Team ID\n"
     "5. Run seed script: python scripts/seed_slack.py\n"
     "6. Add tokens to .env\n\n"
     "Seed script creates #product, #engineering, #customer-feedback, #shipped, #general "
     "with realistic PM conversations about Velocity."},

    {"title": "Set up Linear workspace for demo", "priority": 1,
     "labels": ["integration"], "state": "unstarted",
     "description": "Create Linear workspace for the hackathon demo.\n\n"
     "1. Create workspace at linear.app/new\n"
     "2. Settings → Account → Personal API Keys → Create (Full access)\n"
     "3. Run seed script: python scripts/seed_linear.py\n"
     "4. Add LINEAR_API_KEY to .env\n\n"
     "Seed script creates the full Velocity backlog — 20+ tickets across "
     "Track A-D with real descriptions, priorities, and labels."},

    # =========================================================================
    # Demo prep
    # =========================================================================
    {"title": "Record 3-minute demo video", "priority": 1,
     "labels": ["track-d"], "state": "unstarted",
     "description": "Hackathon submission requires a demo video.\n\n"
     "Demo script:\n"
     "1. Show the product — chat UI, agent activity panel\n"
     "2. Ask 'What should we prioritize this sprint?' — show multi-agent orchestration\n"
     "3. Show cross-source synthesis (Slack discussions + Linear tickets + web research)\n"
     "4. Ask for a sprint update doc — show doc-writer agent\n"
     "5. Show persistence — restart, sessions still there\n\n"
     "Deadline: Feb 16, 3:00 PM EST."},

    {"title": "Write hackathon submission (100-200 words + README)", "priority": 1,
     "labels": ["track-d"], "state": "unstarted",
     "description": "Submission requirements:\n"
     "- 100-200 word summary\n"
     "- GitHub repo with README\n"
     "- Working deployed app URL\n"
     "- Demo video link\n\n"
     "Key points to hit:\n"
     "- Multi-agent orchestration with Opus 4.6\n"
     "- Cross-source synthesis (Slack + Linear + web)\n"
     "- 1M context window for full product context\n"
     "- Persistent memory across sessions\n"
     "- Dogfooding: we used Velocity to build Velocity"},
]

for ticket in TICKETS:
    # Map state names to IDs
    state_name = ticket.get("state", "unstarted")
    state_id = states.get(state_name, states.get("unstarted"))

    issue_input = {
        "title": ticket["title"],
        "description": ticket.get("description", ""),
        "priority": ticket["priority"],
        "teamId": team_id,
        "stateId": state_id,
    }

    # Attach labels
    ticket_label_ids = []
    for label_name in ticket.get("labels", []):
        if label_name in label_ids:
            ticket_label_ids.append(label_ids[label_name])
    if ticket_label_ids:
        issue_input["labelIds"] = ticket_label_ids

    if project_id:
        issue_input["projectId"] = project_id

    try:
        result = gql(
            """
            mutation($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    issue { id identifier title }
                    success
                }
            }
            """,
            {"input": issue_input},
        )
        issue = result["issueCreate"]["issue"]
        status = "✅" if state_name == "done" else "🔧" if state_name == "started" else "📋"
        print(f"  {status} [{issue['identifier']}] {issue['title']}")
    except Exception as e:
        print(f"  Failed: '{ticket['title']}': {e}")

print("\n✅ Done! Linear workspace has the full Velocity backlog.")
print("The backlog agent can now read real project state.")

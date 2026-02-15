# Integration Setup — Quick Start

Complete setup for Slack + Linear integrations with demo data.
Total time: ~20-30 minutes.

---

## 1. Linear (~10 min)

### Create workspace
1. Go to **https://linear.app/new**
2. Workspace name: **Velocity** (or anything)
3. Complete onboarding (create a team — name doesn't matter, the seed script uses the first team)

### Get API key
1. Click your avatar (bottom-left) → **Settings**
2. **Account → Security & Access → Personal API Keys**
3. **Create key** → label "Velocity" → **Full access**
4. Copy the key (`lin_api_...`)

### Add to .env
```bash
# In backend/.env
LINEAR_API_KEY=lin_api_your_key_here
```

### Seed demo data
```bash
cd /home/naga/Development/velocity
LINEAR_API_KEY=lin_api_xxx python scripts/seed_linear.py
```

Creates: 1 project, 9 labels, 25+ tickets (Track A-D work items, bugs, integration tasks, demo prep) with real Velocity descriptions and priorities.

---

## 2. Slack (~15 min)

### Create workspace
1. Go to **https://slack.com/get-started#/createnew**
2. Workspace name: **Velocity PM** (or anything)
3. Skip inviting people, skip channel setup

### Create bot app
1. Go to **https://api.slack.com/apps**
2. **Create New App → From scratch**
3. App name: **Velocity PM Bot**
4. Select your new workspace
5. Click **Create App**

### Configure scopes
1. Left sidebar → **OAuth & Permissions**
2. Scroll to **Bot Token Scopes**, add:
   - `channels:history` — read channel messages
   - `channels:read` — list channels
   - `channels:manage` — create channels (for seed script)
   - `chat:write` — post messages
   - `reactions:write` — add reactions
   - `users:read` — list users
   - `users.profile:read` — user profiles

### Install & get tokens
1. Scroll up → **Install to Workspace** → Allow
2. Copy **Bot User OAuth Token** (`xoxb-...`)
3. Get **Team ID**: open Slack in browser, URL is `https://app.slack.com/client/TXXXXXXXX/...` — copy the `T...` part

### Add to .env
```bash
# In backend/.env
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_TEAM_ID=TXXXXXXXX
```

### Seed demo data
```bash
cd /home/naga/Development/velocity
SLACK_BOT_TOKEN=xoxb-xxx python scripts/seed_slack.py
```

Creates: 5 channels (#product, #engineering, #customer-feedback, #shipped, #general) with conversations about Velocity — architecture decisions, SDK bugs, customer interviews, shipped updates, sprint planning.

### Invite bot to channels
In each channel, type: `/invite @Velocity PM Bot`

---

## 3. Verify .env

Your `backend/.env` should now have:
```bash
ANTHROPIC_API_KEY=sk-ant-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_TEAM_ID=T...
LINEAR_API_KEY=lin_api_...
REDIS_URL=redis://localhost:6379
DATABASE_URL=sqlite:///./data/app.db
FRONTEND_URL=http://localhost:3000
```

---

## 4. Code fixes needed

Before testing, `agent.py` needs updates:
- Fix MCP package names (current ones don't exist on npm)
- Add SLACK_TEAM_ID to config.py and MCP server env

These fixes are tracked in the Linear backlog (ticket: "MCP package names in agent.py are wrong").

---

## What the seed data enables

Once tokens are configured:

**"What should we prioritize this sprint?"**
→ Research agent searches #product and #customer-feedback in Slack
→ Backlog agent reads Linear tickets, sees priorities and blockers
→ Prioritization agent combines both, applies RICE scoring
→ Orchestrator synthesizes with citations from both sources

**"Write a sprint update for stakeholders"**
→ Backlog agent reads what shipped (Linear: done tickets)
→ Research agent checks #shipped channel in Slack
→ Doc-writer generates a grounded update with ticket links

**"What are customers saying about prioritization?"**
→ Research agent searches #customer-feedback
→ Finds PM quotes about RICE, hallucination concerns, speed requirements
→ Returns structured findings with source links

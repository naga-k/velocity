#!/usr/bin/env python3
"""Seed a Slack workspace with Velocity project conversations.

Usage:
    SLACK_BOT_TOKEN=xoxb-xxx python scripts/seed_slack.py

Creates channels and posts conversations about the actual Velocity project —
architecture decisions, engineering challenges, customer feedback, shipped
updates. Dogfooding: the agent reads conversations about itself.

Note: Bot needs 'channels:manage' scope to create channels. If you don't
have it, create channels manually and pass them:
    CHANNEL_IDS='product:C123,engineering:C456,...' python scripts/seed_slack.py
"""

import json
import os
import sys
import time
import urllib.request

BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
if not BOT_TOKEN:
    print("ERROR: Set SLACK_BOT_TOKEN environment variable")
    sys.exit(1)


def slack_api(method: str, params: dict | None = None) -> dict:
    url = f"https://slack.com/api/{method}"
    data = json.dumps(params or {}).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {BOT_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        print(f"  Slack API error ({method}): {result.get('error', 'unknown')}")
    return result


def create_channel(name: str) -> str | None:
    result = slack_api("conversations.create", {"name": name, "is_private": False})
    if result.get("ok"):
        ch_id = result["channel"]["id"]
        print(f"  Created #{name} ({ch_id})")
        return ch_id
    if result.get("error") == "name_taken":
        list_result = slack_api("conversations.list", {"types": "public_channel", "limit": 200})
        if list_result.get("ok"):
            for ch in list_result.get("channels", []):
                if ch["name"] == name:
                    print(f"  #{name} already exists ({ch['id']})")
                    return ch["id"]
    return None


def post(channel_id: str, text: str, thread_ts: str | None = None) -> str | None:
    params = {"channel": channel_id, "text": text}
    if thread_ts:
        params["thread_ts"] = thread_ts
    result = slack_api("chat.postMessage", params)
    time.sleep(0.3)  # Rate limit
    return result.get("ts")


# --- Create channels ---
print("Creating channels...")
CHANNELS = {
    "product": "Product decisions, roadmap, and priorities for Velocity",
    "engineering": "Technical discussions, architecture, and SDK issues",
    "customer-feedback": "PM feedback, beta user insights, and feature requests",
    "shipped": "What we shipped — track releases and progress",
    "general": "Team updates and hackathon coordination",
}

channel_ids = {}
for name, purpose in CHANNELS.items():
    ch_id = create_channel(name)
    if ch_id:
        channel_ids[name] = ch_id
        slack_api("conversations.setPurpose", {"channel": ch_id, "purpose": purpose})

# Try manual channel IDs if creation failed
if not channel_ids:
    manual = os.environ.get("CHANNEL_IDS", "")
    if manual:
        for pair in manual.split(","):
            name, cid = pair.split(":")
            channel_ids[name.strip()] = cid.strip()
    else:
        print("\nNo channels created. Bot needs 'channels:manage' scope.")
        print("Create channels manually and pass: CHANNEL_IDS='product:C123,...'")
        sys.exit(1)

# =========================================================================
# #product — Architecture decisions & roadmap
# =========================================================================
print("\nSeeding #product...")
if "product" in channel_ids:
    ch = channel_ids["product"]

    ts = post(ch, "*Architecture Decision: Claude Agent SDK IS the orchestrator*\n\n"
              "After evaluating options (custom orchestrator, LangGraph hybrid, raw API), "
              "we're going with the Claude Agent SDK as the orchestrator. Not a wrapper we build around.\n\n"
              "Reasons:\n"
              "- SDK handles agent loop, tool execution, compaction, streaming natively\n"
              "- Subagents via AgentDefinition — no custom classes needed\n"
              "- MCP integration built in\n"
              "- bypassPermissions mode for hackathon\n\n"
              "The backend becomes a thin SSE bridge. All agent logic lives in SDK configuration.")
    if ts:
        post(ch, "This is the right call. We were over-engineering with the custom orchestrator. "
             "The SDK handles 80% of what we'd build ourselves.", ts)
        post(ch, "Agreed. One concern: the SDK's resume feature is broken (returns empty responses). "
             "Means no multi-turn context. Each message is independent.", ts)
        post(ch, "Workaround: fresh client per query. Not ideal but works for the demo. "
             "Submitted PR #572 upstream for the fix.", ts)

    ts = post(ch, "*Roadmap for hackathon (Feb 10-16):*\n\n"
              "- Track A: Agent SDK + MCP integration ✅ DONE\n"
              "- Track B: Frontend UI/UX — agent activity, source cards, polish\n"
              "- Track C: Memory + persistence (SQLite + Redis) ✅ DONE\n"
              "- Track D: Deployment (Railway + Vercel) + demo prep\n\n"
              "Day 5 (today): Get integrations live with real Slack/Linear data, frontend improvements, deploy.\n"
              "Day 6 (tomorrow): Demo video, submission, polish.")
    if ts:
        post(ch, "We should prioritize making the cross-source synthesis demo really solid. "
             "That's our differentiator — asking 'what should we prioritize?' and seeing it "
             "pull from Slack, Linear, AND web search simultaneously.", ts)
        post(ch, "Yes. The multi-agent orchestration is what makes this an Opus 4.6 showcase. "
             "Sonnet can't reliably coordinate 4 subagents.", ts)

    ts = post(ch, "*Decision: RICE framework for prioritization agent*\n\n"
              "The prioritization agent will use RICE scoring by default:\n"
              "- Reach: users affected per quarter\n"
              "- Impact: 3=massive, 2=high, 1=medium, 0.5=low\n"
              "- Confidence: 100%/80%/50% based on evidence quality\n"
              "- Effort: person-weeks\n\n"
              "Score = (Reach × Impact × Confidence) / Effort\n\n"
              "The agent should also flag when confidence is low — challenge our assumptions, "
              "not just rubber-stamp them.")

    post(ch, "*Competitive landscape update:*\n\n"
         "- Productboard launched an AI assistant — GPT on their feature voting board. Very narrow, only works with Productboard data.\n"
         "- Linear just added AI project summaries — nice but it's single-source (Linear only).\n"
         "- No one is doing cross-source synthesis across Slack + Linear + web yet.\n\n"
         "Our angle: multi-source context assembly. The thing PMs spend 3 hours/day doing manually.")

    ts = post(ch, "YC's latest RFS explicitly calls out 'Cursor for Product Managers'. "
              "That's literally what we're building. Quote: 'An AI-native tool that helps PMs "
              "make better decisions by connecting the dots across their tools.'\n\n"
              "Link: https://www.ycombinator.com/rfs#cursor-for-product-managers")
    if ts:
        post(ch, "This validates the approach. Key difference from existing tools: "
             "they're all single-source (Productboard = feature votes, Linear = tickets). "
             "We connect ALL the sources.", ts)

# =========================================================================
# #engineering — Technical discussions
# =========================================================================
print("Seeding #engineering...")
if "engineering" in channel_ids:
    ch = channel_ids["engineering"]

    ts = post(ch, "*SDK Bug Report: Buffer Deadlock (#558)*\n\n"
              "Found a deadlock in the Claude Agent SDK's message stream handling. "
              "When subagents make multiple tool calls rapidly, the buffer fills up "
              "and the SDK hangs indefinitely.\n\n"
              "Fix: Fork at `naga-k/claude-agent-sdk-python` branch `fix/558-message-buffer-deadlock`. "
              "Installed via `[tool.uv.sources]` git override.\n\n"
              "Upstream PR submitted.")
    if ts:
        post(ch, "Good catch. This was blocking the entire multi-agent flow. "
             "Without the fix, any query that triggers >2 tool calls in a subagent would hang.", ts)

    ts = post(ch, "*Token usage analysis (last 24h of testing):*\n\n"
              "- Orchestrator (Opus 4.6): ~45K input, ~12K output per query\n"
              "- Research Agent (Sonnet 4.5): ~20K input, ~5K output per invocation\n"
              "- Backlog Agent (Sonnet 4.5): ~15K input, ~3K output per invocation\n"
              "- Prioritization (Opus 4.6): ~30K input, ~8K output per invocation\n\n"
              "Multi-agent query cost: ~$0.50-$1.50 depending on complexity.\n"
              "At max burn rate, $500 credits last ~5 days of heavy usage.\n\n"
              "We should add caching for repeat queries via Redis.")
    if ts:
        post(ch, "The max_budget_per_session_usd is set to $2.00 in config. "
             "That's enough for 1-2 complex multi-agent queries per session. "
             "Should we raise it?", ts)
        post(ch, "Keep it at $2 for now. If someone asks a simple question, "
             "Opus won't invoke subagents and it'll cost $0.10. The budget is per session, not per query.", ts)

    post(ch, "*Architecture note: Three-layer bridge pattern*\n\n"
         "The streaming pipeline is: `routes/chat.py → agent.py → sse_bridge.py`\n\n"
         "- `chat.py` is ultra-thin — receives request, passes to generate_response, wraps in EventSourceResponse\n"
         "- `agent.py` has all SDK logic — generate_response() yields (event_type, json_data) tuples\n"
         "- `sse_bridge.py` translates tuples to ServerSentEvent objects\n\n"
         "Each layer is independently testable. 58 tests cover the full pipeline.\n"
         "When we add features (citations, etc.), only agent.py needs to change.")

    ts = post(ch, "*Issue: Fresh client per query means no conversation memory*\n\n"
              "Because SDK resume is broken, each message creates a new ClaudeSDKClient. "
              "The agent has zero memory of what was said 30 seconds ago.\n\n"
              "Proposed fix: inject last 3-5 messages from session_store into the system prompt. "
              "session_store.get_session_context() already returns the message history.\n\n"
              "It's not real multi-turn, but it's way better than amnesia.")
    if ts:
        post(ch, "This is critical for the demo. If someone asks a follow-up question "
             "and the agent has no idea what they were talking about, it looks broken.", ts)
        post(ch, "I'll wire this up. The session_store API is ready (Track C). "
             "Just need to modify generate_response() to load context and prepend to the system prompt.", ts)

    post(ch, "*MCP package names are wrong in agent.py!*\n\n"
         "`@anthropic/slack-mcp` and `@anthropic/linear-mcp` don't exist on npm.\n\n"
         "Real packages:\n"
         "- Slack: `@modelcontextprotocol/server-slack` (or community fork `slack-mcp-server`)\n"
         "- Linear: `linear-mcp` (stdio) or official `mcp.linear.app` (HTTP)\n\n"
         "Also missing SLACK_TEAM_ID in config — the Slack MCP server requires it.\n"
         "Need to fix before we can test integrations with real tokens.")

# =========================================================================
# #customer-feedback — Beta user insights
# =========================================================================
print("Seeding #customer-feedback...")
if "customer-feedback" in channel_ids:
    ch = channel_ids["customer-feedback"]

    post(ch, "*PM at a Series A startup (user interview):*\n\n"
         "\"I spend about 3 hours every Monday morning just reading Slack and Linear to understand "
         "what happened last week before I can plan this week. By the time I have context, "
         "it's lunch and I haven't made a single decision.\"\n\n"
         "\"If an AI could do that context assembly for me in 30 seconds, I'd pay for it immediately.\"")

    post(ch, "*Founder/PM at 5-person startup:*\n\n"
         "\"I don't need another project management tool. I need something that connects "
         "the tools I already have. My context is split across Slack, Linear, Notion, and "
         "Google Docs. No single tool has the full picture.\"\n\n"
         "\"The cross-source thing is the killer feature. If it can tell me 'here's what "
         "customers are saying in Slack + here's what's in your backlog + here's what "
         "competitors are doing' in one answer, that's magic.\"")

    post(ch, "*PM at a Series B company:*\n\n"
         "\"I tried using ChatGPT for PM work. It's good for writing but useless for decisions "
         "because it doesn't know anything about our product, our users, or our data. "
         "I have to paste context every time.\"\n\n"
         "\"What I want is an AI that already knows my product — has read all the Slack threads, "
         "seen the backlog, knows the metrics. Persistent context is the key.\"")

    ts = post(ch, "*Feature request pattern (3 users this week):*\n\n"
              "Multiple PMs asking about exporting agent recommendations. They want to:\n"
              "1. Share prioritization output with their team (Notion or Google Docs)\n"
              "2. Turn agent research into a stakeholder update\n"
              "3. Copy recommendations into sprint planning docs\n\n"
              "This maps directly to the doc-writer agent + Notion integration.")
    if ts:
        post(ch, "The doc-writer agent is defined but hasn't been tested with real data yet. "
             "Once integrations are live, we should test: 'Write a sprint update based on "
             "what shipped this week and what's blocked.'", ts)

    post(ch, "*Concern from a PM:*\n\n"
         "\"I worry about the AI hallucinating metrics. If it tells me 'feature adoption is 67%' "
         "and that's wrong, I might make a bad decision based on it. Every number needs a source.\"\n\n"
         "This is exactly why we have P4: Ground truth at every step. Every claim must cite a source. "
         "No hallucinated metrics, no ungrounded recommendations.")

    post(ch, "*PM at a growth-stage startup:*\n\n"
         "\"The agent activity panel is brilliant. Seeing it search Slack, then read Linear, "
         "then synthesize — it feels like watching a junior PM do the legwork. "
         "But it needs to be fast. If it takes more than 30 seconds, I'll just do it myself.\"\n\n"
         "Performance is critical. Parallel subagent execution helps. Showing activity keeps "
         "users engaged during longer queries.")

# =========================================================================
# #shipped — Release log
# =========================================================================
print("Seeding #shipped...")
if "shipped" in channel_ids:
    ch = channel_ids["shipped"]

    post(ch, ":rocket: *Track A: Claude Agent SDK Integration — SHIPPED*\n\n"
         "Replaced the scaffold Anthropic API with Claude Agent SDK.\n\n"
         "What's new:\n"
         "- Opus 4.6 orchestrator with adaptive thinking\n"
         "- 4 subagents defined: research, backlog, prioritization, doc-writer\n"
         "- Slack + Linear MCP configured (conditional on credentials)\n"
         "- Custom PM tools: read_product_context, save_insight\n"
         "- Three-layer bridge: routes → agent → sse_bridge\n"
         "- SDK bug workarounds: fresh-client-per-query, buffer deadlock fix\n"
         "- 58 backend tests passing\n\n"
         "The agent can autonomously decide which subagent to invoke. Subagent dispatch "
         "verified — backlog agent ran Glob/Grep/Read/Bash tools successfully.")

    post(ch, ":rocket: *Track C: Memory & Persistence — SHIPPED*\n\n"
         "Three-tier persistence layer:\n\n"
         "- *SQLite* (aiosqlite): sessions + messages tables, FK cascade, indexed\n"
         "- *Redis* (redis.asyncio): cache with TTL, session state, graceful fallback\n"
         "- *File-based*: product-context.md, decisions/, insights/\n\n"
         "Key features:\n"
         "- Sessions persist across server restart\n"
         "- Redis is optional — app runs without it (warning, not error)\n"
         "- session_store.get_session_context() for agent context loading\n"
         "- 95 tests passing (58 Track A + 37 Track C)\n\n"
         "PR #3 ready to merge to main.")

    post(ch, ":rocket: *Day 3: Foundation — SHIPPED*\n\n"
         "Project scaffolding complete:\n"
         "- FastAPI + Next.js monorepo\n"
         "- Docker Compose (backend + Redis)\n"
         "- Basic SSE streaming endpoint\n"
         "- Minimal chat UI (message input + streaming response)\n"
         "- 40 backend tests passing")

# =========================================================================
# #general — Coordination
# =========================================================================
print("Seeding #general...")
if "general" in channel_ids:
    ch = channel_ids["general"]

    post(ch, "*Hackathon Day 5 Status (Feb 14):*\n\n"
         "Backend is solid — 95 tests, Agent SDK integrated, persistence working.\n\n"
         "Today's priorities:\n"
         "1. Set up Slack + Linear workspaces with demo data\n"
         "2. Fix MCP package names and test real integrations\n"
         "3. Wire session context into agent (conversation memory)\n"
         "4. Frontend: markdown rendering, agent activity, session sidebar\n"
         "5. Deploy to Railway + Vercel\n\n"
         "Deadline: Sunday Feb 16, 3:00 PM EST.\n"
         "Deliverables: 3-min demo video, 100-200 word summary, deployed app, GitHub repo.")

    ts = post(ch, "The demo story should be: PM asks 'what should we prioritize for the next sprint?' "
              "and the agent:\n\n"
              "1. Shows agent activity (research agent searching Slack, backlog agent reading Linear)\n"
              "2. Pulls real data from multiple sources\n"
              "3. Synthesizes with citations\n"
              "4. Gives a ranked recommendation with evidence\n\n"
              "Then ask it to write a sprint update doc. Two queries, shows the whole product.")
    if ts:
        post(ch, "I'd also show the persistence — restart the server, sessions are still there. "
             "That's a subtle but important differentiator.", ts)
        post(ch, "And the dogfooding angle — we're using Velocity to manage Velocity. "
             "The agent is reading conversations about itself. Very meta, judges will love it.", ts)

    post(ch, "*Cost tracking:* We have $500 in Anthropic API credits. "
         "At ~$1 per complex query, that's ~500 queries. "
         "Plenty for demo + some real usage. "
         "Per-session budget is capped at $2.00 via max_budget_per_session_usd.")


print("\n✅ Done! Slack workspace seeded with Velocity project conversations.")
print("\nChannels seeded:")
for name, ch_id in channel_ids.items():
    print(f"  #{name} ({ch_id})")
print("\nRemember to invite the bot to each channel: /invite @Velocity PM Bot")

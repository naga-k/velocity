# PRD: AI PM Agent

**Status:** Draft — living doc, will keep updating
**Last updated:** Feb 12, 2026

---

## What Is This

An agentic AI tool for startup PMs that connects to their existing tools and helps them make better product decisions. It pulls together external signals (user feedback, research, analytics) and internal state (backlog, roadmap, team work) so PMs spend less time gathering context and more time thinking.

It covers the full decision cycle: from research and data analysis, through prioritization, all the way to generating the output docs (specs, PRDs, updates).

---

## Who Is This For

- Startup PMs (seed through Series B)
- Founders doing PM work at early stage
- Could extend to GTM roles later (shared DNA between PM and GTM workflows)

---

## Core Problem

PMs spend 50-75% of their time just assembling context — digging through Slack, checking dashboards, reading support tickets, searching Linear for what shipped. The actual strategic thinking (what should we build and why) gets squeezed into whatever time is left.

The information exists. It's just scattered across 6-10 tools and nobody's connecting it.

---

## Two Main Inputs

### 1. External Signals
What's happening outside the team — what users want, what the market looks like, what the data says.

- **User/customer feedback** — support tickets (Intercom), Slack messages from customers, survey responses
- **User research** — interview transcripts, research notes, patterns across conversations
- **Product analytics** — feature adoption, retention, funnels, anomalies (Amplitude/Mixpanel)
- **Market/competitive intel** — what competitors are doing, market trends, new entrants

### 2. Internal State
What's happening inside the team — what's being built, what shipped, what's stuck.

- **Backlog** — all tickets, their status, priority, who's assigned (Linear)
- **Roadmap** — what's planned, what's in progress, what's done
- **Team capacity** — who's working on what, what's blocked, velocity
- **Past decisions** — what was decided, why, and what happened after

---

## Core Feature Areas

### User & Market Research
- Synthesize customer feedback across sources (Intercom, Slack, surveys) — surface patterns, not just summaries
- Analyze user interview transcripts — extract themes, contradictions, insights
- Competitive analysis — track what competitors are shipping, how we compare
- Market trend tracking — pull signals from web, news, industry reports
- Maintain a persistent **insight graph** that accumulates knowledge over time (not starting fresh every session)

### Data Analysis
- Pull product metrics from Amplitude/Mixpanel — adoption, retention, funnels
- Spot anomalies and trends automatically ("signups dropped 15% this week")
- Answer ad hoc data questions in natural language ("how many users hit the new onboarding flow last week")
- Ground every recommendation in actual data, not vibes

### Backlog & Prioritization
- Pull all signals together — feedback + data + research + internal state
- Help rank what to build next using evidence, not gut feel
- Score features against frameworks (impact vs effort, RICE, or custom)
- Surface evidence for or against a feature idea ("12 users requested this, adoption of similar feature is 34%, competitor X just shipped it")
- Flag conflicts ("this ticket contradicts the decision we made in November")

### Document Generation
- Once research + data + prioritization point to a decision, generate the output doc (PRD, one-pager, stakeholder update)
- Docs are grounded in the actual research and data — not generic templates
- Coaching mode: upload an existing doc and get feedback (missing sections, weak reasoning, contradictions with data)
- Push output to connected tools (Notion, Linear tickets, Slack)

---

## Integrations

### Starting Integration
- **Linear** — backlog, tickets, roadmap, sprints, team assignments

### Tier 1 (Core)
- **Slack** — where 80% of context lives. Discussions, decisions, customer feedback channels
- **Linear** — backlog, roadmap, sprint data, ticket status
- **Notion** — specs, meeting notes, decision logs, research repos

### Tier 2 (High Priority)
- **Amplitude / Mixpanel** — product analytics, metrics, funnels
- **Intercom / Zendesk** — customer feedback, support tickets
- **Figma** — design context

### Tier 3 (GTM Extension)
- **HubSpot / Salesforce** — deal pipeline, customer data
- **Apollo / Clay** — prospect data, enrichment
- **Gong** — sales call transcripts, conversation intelligence

### Nice to Have
- Google Calendar — meeting context
- Fireflies / Otter — meeting transcripts
- Dovetail — research repository
- Google Docs — collaborative docs

---

## Architecture

### Built On
- **Claude Agent SDK** (TypeScript or Python) — the backend brain
- **FastAPI** backend — Vercel has quick timeouts, agentic tasks run long. FastAPI handles long-running agent sessions, streaming responses back to the frontend.
- **Next.js** frontend — standalone SaaS app with its own UI
- Chat-based interface as the primary interaction model

### Creative Uses of Opus 4.6
This is a hackathon for Opus 4.6. The app should showcase what makes it special:
- **1M token context window** — load an entire product's worth of context (all Linear tickets, Slack history, Notion docs, analytics) into a single session. No other model can hold this much product context at once.
- **128K output tokens** — generate comprehensive research reports, full PRDs, and detailed prioritization analyses in a single pass instead of chunking.
- **Multi-agent orchestration** — Opus 4.6's reasoning quality makes it reliable enough to coordinate specialized subagents autonomously.
- **Deep reasoning on complex trade-offs** — prioritization requires weighing incomplete, contradictory evidence. This is where Opus shines over smaller models.

### Agentic Design
The app uses **subagents** — specialized agents that each handle a focused task, coordinated by a main orchestrator. This mirrors how a PM team works: different people with different expertise, all contributing to decisions.

**Proposed agents:**
- **Research Agent** — pulls and synthesizes data from external sources (Slack, Intercom, web)
- **Data Agent** — connects to analytics, answers metric questions, spots trends
- **Backlog Agent** — reads Linear state, understands what's in-flight, what shipped, what's stuck
- **Prioritization Agent** — takes inputs from the other agents and helps rank/score/decide
- **Doc Agent** — generates PRDs, one-pagers, updates grounded in research/data. Also reviews existing docs.

**MCP Connections** — each integration (Slack, Linear, Notion, Amplitude, etc.) connects via Model Context Protocol

**Persistent Memory** — accumulated product knowledge survives across sessions. Past decisions, research insights, metric baselines. The app gets smarter the more you use it.

**Hooks** — quality gates that run automatically:
- After research synthesis: flag if sources are thin or contradictory
- After prioritization: check that data actually supports the ranking
- After any recommendation: cite sources so PM can verify

---

## UI

### Design Philosophy
UI is a first-class priority, not an afterthought. This needs to look and feel like a premium product from day one. Judges, users, and investors all form opinions in the first 5 seconds.

### Tech Stack
- **Next.js** — React framework
- **Tailwind CSS** — utility-first styling
- **shadcn/ui** — component library (polished, accessible, customizable)

### Design References
- **Perplexity** — chat-first with rich inline results, citations, source cards
- **Replit** — clean workspace feel, sidebar + main panel, real-time streaming

### Approach (Two Phases)
**Phase 1 (Hackathon):** Basic but clean. Solid colors, no animations, everything works. Focus is on the agent layer and features being functional.

**Phase 2 (Post-hackathon):** Go crazy. Animations, transitions, streaming effects, glassmorphism, whatever makes it feel premium and flashy. The wow factor.

### Core UI Elements
- **Chat-first** — primary interface is a conversation. PM asks questions, agent answers with grounded, cited responses.
- **Rich results** — not just text walls. Inline source cards, data visualizations, ticket previews from Linear, cited evidence.
- **All features present in UI** — even if an integration isn't ready yet, its slot exists in the UI (disabled/coming soon state). The app should feel complete.

---

## Hackathon MVP Scope

For the "Built with Opus 4.6" hackathon (Feb 10-16, 2026):

**In scope:**
- Chat UI (basic)
- Linear integration (MCP)
- Slack integration (MCP)
- Research Agent (synthesize from Slack + web)
- Backlog Agent (read Linear, understand project state)
- Prioritization Agent (combine signals, help rank)
- Persistent memory across sessions
- Demo: use the app on this very project (dogfooding)

**Out of scope for hackathon:**
- Amplitude/Mixpanel integration
- Intercom integration
- Figma integration
- All GTM integrations
- ~~Polished UI~~ **UI polish IS in scope** — needs to be demo-ready and impressive
- Multi-user / team features
- Authentication / user management

---

## Success Metrics (Post-Hackathon)

TBD — to be defined after PM interviews and initial usage.

Likely candidates:
- Time saved on context assembly (before/after)
- Quality of decisions (harder to measure, maybe proxy via confidence or evidence-per-decision)
- Adoption/retention (do PMs keep coming back)

---

## Open Questions

- What prioritization framework do most startup PMs actually use? Or do they just wing it?
- How much do PMs trust AI-generated research vs doing it themselves?
- Is chat the right primary interface, or do PMs want dashboards/views too?
- How to handle data freshness — do we poll integrations, or pull on demand?
- Linear first, but how quickly do we need Jira support to be viable?
- Pricing model?

---

## References

- [Research: What Startup PMs Actually Do & Use](./05-what-startup-pms-actually-do-and-use.md)
- [Market Landscape: AI Tools for PM & GTM](./02-market-landscape.md)
- [Claude Code Architecture for PM/GTM](./03-claude-code-architecture-for-pm-gtm.md)
- [User Stories & Workflows](./04-user-stories-and-workflows.md)
- [Original Cursor-for-PMs Research](./01-cursor-for-pms-original-research.md)

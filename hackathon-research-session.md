# Hackathon Research & Prototyping Session
## Built with Opus 4.6 — Claude Code Hackathon

**Date**: Feb 12, 2026 (Day 3 of hacking, deadline Feb 16 3PM EST)
**Team size**: Solo
**Status**: Exploring — no idea locked in yet

---

## The Core Space: "Cursor for Product Managers"

### The Analogy
Cursor is a fork of VS Code — it didn't reinvent the editor, it took the workspace developers already live in and made it AI-native. The question: **what is the PM equivalent of VS Code, and what does it look like to fork it and make it AI-native?**

This is an open question. Unlike devs who clearly live in their editor, PMs don't have one single workspace. They tab-switch constantly. That fragmentation might itself be the problem — or the opportunity.

### Key Question (Unresolved)
What is the PM's "editor"? Candidates:
- Notion / docs (where specs and decisions get written)
- Spreadsheets (where prioritization actually happens)
- Slack (where context lives and dies)
- There might not be one — and that's the gap

---

## What PMs Actually Do (Workflow Zones)

1. **Feedback collection** — bug reports, feature requests, sales conversations, support tickets, surveys
2. **Synthesis** — turning raw feedback into themes, patterns, priorities
3. **Prioritization** — frameworks like MoSCoW, RICE, HEART
4. **Data analysis** — dashboards, metrics, usage data
5. **Decision & spec** — what to build, why, handing off to engineering
6. **Communication** — roadmaps, stakeholder updates, changelog

---

## Tools Startups & Small Teams Actually Use

### Feedback & Support
- Intercom (very common for startups)
- Crisp
- Zendesk (more mid-size)

### Analytics
- Mixpanel
- PostHog (open source, popular with small teams)
- Amplitude (more established/growth stage)
- Hotjar (heatmaps, session recordings, surveys)

### Error/Performance Monitoring
- Sentry
- New Relic

### Project Tracking
- Linear (dev-loved, startup default)
- Shortcut
- Notion (used for everything)
- Jira (more enterprise but some startups use it)

### Surveys
- Typeform
- Qualtrics (enterprise)

### Communication
- Slack (massive implicit feedback channel)

### Code/Issues
- GitHub

### Data/BI
- Fabi AI — AI-native BI, lets PMs query data without data teams, connects to warehouses, auto-generates SQL/Python. Founded by PMs. Positioned for startup teams who don't have dedicated data analysts.

### Existing PM-specific platforms
- Productboard (feedback + roadmapping, more enterprise pricing)
- Dovetail (user research synthesis)
- Sprig (in-product surveys)
- Airfocus (prioritization + roadmapping)

---

## Direction: Agentic Build

Heavy agentic approach makes sense because:
- $500 in API credits to burn on Opus 4.6 calls
- Anthropic is the judge — they want to see what agents can do with their model
- "Agentic" is where the industry is heading
- 25% of judging is creative Opus 4.6 use — a deeply agentic system showcases this

### What "agentic" could mean here
- **Single agent, deep workflow**: One agent that autonomously moves through a multi-step PM workflow (collect → synthesize → prioritize → output)
- **Multi-agent system**: Specialized agents handing off to each other (feedback agent, analysis agent, prioritization agent, spec-writing agent)
- **Tool-using agent**: Agent that connects to real external services and takes actions (not just a chatbot answering questions)

### The bar to clear
Not just "Claude answers questions about your PM data" — that's a wrapper. The impressive version is an agent that autonomously acts across systems: pulls data, cross-references sources, identifies patterns, makes recommendations, drafts outputs. Multi-step, real integrations, visible reasoning.

### Risk
More autonomy = more impressive but more breakable in a live demo. Need to find the right depth for 4 days solo.

---

## Angles Under Consideration

### Angle 1: The Integration Hub
Build the workspace that connects to tools small teams already use (Intercom, Mixpanel, Hotjar, Linear, Slack, GitHub) and synthesizes everything in one place. PM opens one tool and sees feedback, data, and can prioritize.

**Open question**: Is this too broad for a hackathon? Which 2-3 integrations would you wire up for the demo?

### Angle 2: Build for Anthropic PMs
The judges are Anthropic. If the tool solves a problem Anthropic's PMs specifically face, it resonates during judging. Anthropic PM challenges might include:
- Model performance/safety feedback from users
- Developer community feedback (API, Discord, GitHub issues on SDKs)
- High signal-to-noise ratio from many channels
- Shipping AI products where the feedback loop is different (model behavior reports, prompt-level issues)

**Could demo for Anthropic PMs but keep it general enough for any startup PM.**

**Open question**: What does Anthropic actually use internally? Do they talk about their stack publicly? Need to research.

### Angle 3: Feedback-to-Fix Pipeline
Pull feedback in, synthesize, and push toward actionable specs or tickets.

### Angle 4: The Prioritization Engine
Take raw feedback + usage data signals, apply frameworks (RICE, MoSCoW, HEART) automatically, surface what matters. Less about collection, more about the "so what" step.

### Angle 5: Something Else Entirely
No idea is locked. All of the above could be wrong.

---

## Open Questions to Answer

### Strategic
- [ ] What's the single sharpest pain point? Collection? Synthesis? Prioritization? Handoff?
- [ ] Is the "Cursor for PMs" framing actually right, or is it a different shape?
- [ ] What would make this win vs. just being a cool demo? (Judges care: 30% demo, 25% impact, 25% Opus 4.6 use, 20% depth)
- [ ] Does building for Anthropic PMs specifically give an edge, or does it narrow too much?

### Tactical
- [ ] Which integrations to wire up for a working demo by Feb 16?
- [ ] What can Opus 4.6 do here that Sonnet can't? (1M token context, deeper reasoning — how to showcase this?)
- [ ] What's the simplest architecture that still impresses?
- [ ] Can this be launched on Product Hunt for real traction signal?

### From Today's Event
- [ ] Ask PMs: Where do you spend the most time moving information between tools?
- [ ] Ask PMs: What tool do you wish existed?
- [ ] Ask founders: What does your PM stack look like? What's duct-taped together?
- [ ] Ask devs: What's the worst part of getting specs/requirements from PMs?

---

## Hackathon Constraints & Judging Reminder

- **Deadline**: Feb 16, 3:00 PM EST (4 days left)
- **Solo team**
- **Must be open source, built from scratch**
- **Submission**: 3-min demo video, GitHub repo, 100-200 word summary

### Available Resources
- $500 Claude API credits (expire after hackathon)
- Claude Max subscription
- Willing to pay for other tools/services as needed

### Judging Criteria
- **Demo (30%)** — Does it work? Is it impressive live?
- **Impact (25%)** — Real-world potential, who benefits
- **Opus 4.6 Use (25%)** — Creative, beyond basic integration
- **Depth & Execution (20%)** — Pushed past first idea, solid engineering

---

## What Still Needs to Happen

1. Research: Anthropic internal tooling (if public info exists)
2. Research: Competitors more deeply — what do Productboard, Dovetail, etc. actually fail at?
3. Event today: Talk to PMs, founders, devs — validate the pain
4. Decide on an angle
5. Start building

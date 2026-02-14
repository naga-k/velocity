# Cursor for Anthropic PMs: Research & Ideation

---

## Part 1: What Does a PM at Anthropic Actually Do?

Anthropic's PM role is unlike a typical SaaS PM gig. The company operates as a safety-first AI research lab that ships consumer and enterprise products simultaneously. PMs sit at the intersection of cutting-edge research, product delivery, and AI safety policy.

### The PM Org Structure

Anthropic splits their product org into distinct groups — not the typical product/eng binary:

- **Core Product (Claude.ai)** — Owns the fundamental interaction model: how users converse with, instruct, and collaborate with Claude. This PM shapes Claude from "assistant" into "collaborative partner."
- **Claude Code** — Drives the developer tools suite. Works closely with internal power users and external developers to prioritize features and ship improvements that keep pace with model capabilities.
- **Claude Code Growth** — Owns acquisition, retention, monetization, and virality. Runs experiments, analyzes metrics, and launches growth features.
- **Research PM** — Bridges research and product. Owns ideation and deployment of new models, productizes applied research, and identifies high-potential use cases grounded in customer needs.
- **API Platform / MCP** — Builds the developer platform, including Model Context Protocol, which since November 2024 has generated hundreds of community integrations.
- **Labs (Incubator)** — An internal skunkworks led hands-on by Mike Krieger (Instagram co-founder). Rapid prototyping with early users, then scaling what works.

### Day-to-Day Responsibilities

- **Translate research into product requirements** — PMs take alignment and interpretability research and turn it into user-facing specs and ship criteria.
- **Write PRDs (or don't)** — Anthropic is famously prototype-first. The prototype often *becomes* the spec. PMs spend less time writing 30-page docs and more time iterating on working code.
- **Define safety trade-offs** — Every feature involves explicit trade-offs between capability, reliability, and guardrails. PMs own these decisions.
- **Coordinate evals and red-teaming** — PMs define success metrics that balance quality, safety, and speed, then run evaluation loops post-launch.
- **Internal dogfooding ("Antfooding")** — Anthropic's entire technical org acts as a verification system. PMs drive aggressive internal testing and synthesize feedback.
- **Stakeholder communication** — Execs, researchers, engineers, policy teams, enterprise customers — PMs keep all these groups aligned.

### What Makes the Role Unique

1. **Prototype-first culture** — Artifacts was built by one researcher in 3 months. Claude Code started as an internal tool ("Clyde") that got organic adoption. PMs don't gate-keep ideas through specs; they amplify what's already working.
2. **Safety as a first-class product dimension** — PMs evaluate refusal accuracy, harm reduction rates, and trust calibration alongside traditional metrics.
3. **Compounding feedback loops** — They build Claude Code *using* Claude Code. Every improvement to the tool improves how they build the next improvement.
4. **"WIP Wednesdays"** — Internal demo culture where scrappy prototypes get surfaced and tested.

---

## Part 2: The PM Toolkit at Anthropic

### Internal Tools

| Category | Tools |
|----------|-------|
| Project Tracking | Linear, Jira, Asana |
| Knowledge Base | Notion, Google Docs |
| Communication | Slack |
| Design | Figma |
| Analytics | Amplitude, Pendo |
| User Feedback | Intercom, Fireflies |
| Prototyping | Claude Code, v0 |
| AI-Assisted Work | Claude (dogfooded heavily) |

### The Existing PM Plugin (Cowork)

Anthropic already ships a Product Management plugin for Cowork that covers:

- Feature specs & PRDs (via `/product-management:write-spec`)
- Roadmap planning (Now/Next/Later, OKR-aligned)
- Stakeholder updates (audience-tailored)
- User research synthesis
- Competitor analysis
- Metric tracking

It integrates with Slack, Linear, Asana, Monday, ClickUp, Jira, Notion, Figma, Amplitude, Pendo, Intercom, and Fireflies via MCP.

### Current Gaps & Pain Points

1. **Outputs look professional but "fail every reality test"** — The plugin generates polished docs but lacks grounding in the company's actual context, constraints, and tribal knowledge.
2. **Fragmented workflows** — PMs still manually consolidate across Linear, Slack, Notion, Figma, and analytics dashboards.
3. **No persistent project memory** — Each session starts fresh. There's no "codebase" equivalent that gives the AI full context.
4. **Safety trade-off reasoning is manual** — No tool helps PMs systematically evaluate capability vs. safety vs. reliability trade-offs.
5. **Prototype-to-product handoff is ad hoc** — The prototype-first culture is powerful but messy. There's no structured way to capture *why* something worked internally before scaling it externally.

---

## Part 3: The Cursor Analogy — What Makes Cursor Special?

To design a "Cursor for PMs," we need to understand why Cursor works for developers:

| Cursor Feature | Why It Matters |
|---|---|
| **Full codebase indexing** | Cursor understands the *entire* project, not just the open file. Suggestions are contextually grounded. |
| **AI built into the core** | Not a plugin bolted onto VS Code — the editor is redesigned around AI interaction. |
| **Inline editing (Cmd+K)** | Highlight code, describe what you want changed, see a diff. Zero context-switching. |
| **Chat with your code (Cmd+L)** | Ask questions about the codebase in natural language. Great for onboarding and exploration. |
| **Agent Mode** | Give a high-level goal, Cursor figures out which files to create/edit autonomously. |
| **Familiar interface** | It's a VS Code fork — developers keep their muscle memory, extensions, and settings. |

The core insight: **Cursor made AI feel native to the developer's existing workflow, while giving it deep understanding of the full project context.** It didn't ask developers to change how they work — it met them where they were and made everything faster.

---

## Part 4: Ideas for "Cursor for Anthropic PMs"

### The Vision

An **AI-native PM workspace** that has deep, persistent understanding of your product's full context — roadmap, specs, research, metrics, conversations, safety evaluations — and can assist with any PM task without context-switching, the same way Cursor understands an entire codebase.

### Core Architectural Principles

1. **Full "product-base" indexing** (the PM equivalent of codebase indexing)
   - On setup, the tool indexes your Linear board, Notion workspace, Slack channels, Figma files, Amplitude dashboards, and past PRDs/specs.
   - Creates vector embeddings of all product context — decisions, rationale, metrics, user feedback, safety evaluations.
   - Every AI suggestion is grounded in *your actual product*, not generic PM templates.

2. **AI native, not AI bolted-on**
   - Not a Notion plugin or a Slack bot. A standalone workspace purpose-built for PM workflows.
   - Every view (roadmap, spec editor, metrics dashboard, stakeholder update) has AI woven into it.

3. **Familiar PM primitives**
   - Keeps the mental models PMs already use: epics, stories, roadmap lanes, PRDs, stakeholder tiers.
   - Imports from and syncs back to existing tools (Linear, Notion, etc.) rather than replacing them.

### Feature Ideas

#### 1. **"Cmd+K" for PRDs — Inline Spec Editing**
You're writing a PRD. Highlight a section describing user flows, hit a shortcut, type "add error states and edge cases based on our Slack discussion from last Tuesday." The tool pulls the actual Slack thread, synthesizes the discussion, and proposes additions as a tracked-changes diff you can accept or reject.

#### 2. **"Cmd+L" for Product Context — Chat With Your Product**
A persistent chat sidebar where you can ask:
- "What did we decide about the rate limiting approach for enterprise customers?"
- "Show me all user feedback about onboarding friction in the last 30 days"
- "What are the open safety concerns for the new tool-use feature?"
- "How does this feature relate to our Q2 OKRs?"

It searches across your indexed Slack, Notion, Linear, and Intercom data and gives cited, grounded answers.

#### 3. **Agent Mode for PMs — "Ship This Update"**
Give a high-level instruction like "Prepare the weekly stakeholder update for the Claude Code team." The agent autonomously:
- Pulls completed Linear tickets from the past week
- Summarizes key Slack discussions
- Checks Amplitude for metric changes
- Drafts an update tailored to the exec audience
- Queues it in your preferred format (Slack message, email, Notion page)

You review, edit, and send.

#### 4. **Safety Trade-off Workbench**
A structured workspace unique to AI-company PMs. When scoping a new feature:
- Automatically surfaces related safety evaluations and red-team findings
- Presents a capability vs. safety vs. reliability trade-off matrix
- Shows how similar decisions were made for past features (e.g., "When we shipped Artifacts, we chose X because Y")
- Generates draft evaluation criteria and launch gating conditions

#### 5. **"Antfooding" Dashboard — Internal Usage Intelligence**
Since Anthropic relies heavily on internal dogfooding:
- Tracks internal usage of prototype features
- Surfaces qualitative feedback from internal Slack channels
- Identifies patterns: "17 people tried the new feature, 12 kept using it, 5 stopped — here's why based on their feedback"
- Suggests when a prototype is ready to move from internal to external

#### 6. **Roadmap Copilot — Living, Breathing Roadmap**
Not a static spreadsheet. A dynamic roadmap that:
- Auto-updates based on Linear ticket status
- Flags when dependencies are at risk ("The API team's timeline slipped 2 weeks — this affects your launch")
- Suggests reprioritization based on incoming user feedback trends and metric changes
- Generates "what changed and why" diffs when the roadmap is updated

#### 7. **User Research Synthesizer — Beyond Summaries**
When user research comes in (from Intercom, Fireflies transcripts, survey data):
- Doesn't just summarize — it maps findings to existing product hypotheses
- Identifies contradictions with previous research
- Suggests which roadmap items are validated, invalidated, or need more signal
- Maintains a persistent "insight graph" that accumulates knowledge over time

#### 8. **Spec Reviewer — AI Red Team for PRDs**
Before sharing a PRD, run it through an AI reviewer that:
- Checks for internal consistency
- Flags undefined edge cases
- Cross-references against existing specs for conflicts
- Evaluates against Anthropic's Responsible Scaling Policy
- Simulates questions from different stakeholders ("An engineer would ask X, a safety researcher would ask Y, an exec would ask Z")

#### 9. **Meeting Prep & Debrief Mode**
Before a meeting:
- Pulls relevant context from all integrated tools
- Generates a briefing doc with key decisions needed, open questions, and relevant metrics

After a meeting:
- Transcribes (via Fireflies integration) and extracts action items
- Auto-creates Linear tickets for engineering follow-ups
- Updates relevant Notion docs with decisions made
- Drafts follow-up messages for stakeholders who weren't present

#### 10. **"WIP Wednesday" Prototype Tracker**
Built around Anthropic's internal demo culture:
- Researchers and engineers log prototypes they've built
- PMs can browse, tag, and "watch" prototypes
- AI suggests which prototypes align with roadmap gaps or emerging user needs
- Tracks the journey from demo → internal dogfooding → external launch

---

## Part 5: What Would Make This a "Cursor-Level" Product?

The reason Cursor succeeded wasn't just features — it was the *feeling* of using it. Here's what would make a PM tool feel the same way:

1. **Speed** — Responses in milliseconds, not seconds. Autocomplete for PM work. Start typing a spec and it finishes your sentence with product-context-aware suggestions.

2. **Grounding** — Every suggestion is rooted in your actual product data. No hallucinated metrics, no generic templates. If it references a decision, it cites the Slack thread.

3. **Diff-based editing** — Never overwrites your work. Shows proposed changes as diffs you can accept, reject, or modify — just like Cursor's inline editing.

4. **Compounding intelligence** — Gets smarter the more you use it. Learns your writing style, your team's naming conventions, your stakeholders' preferences, your company's safety framework.

5. **Meets PMs where they are** — Doesn't replace Linear or Notion. Sits on top of them and makes them 10x more useful. Like how Cursor is a VS Code fork, not a brand-new editor.

6. **Works at the speed of thought** — A PM should be able to go from "I have an idea" to "Here's a grounded, context-aware spec with safety considerations, linked to our roadmap, with stakeholder-appropriate summaries" in minutes, not days.

---

## Summary

The gap in the market isn't "AI that writes PRDs" — that already exists and the outputs are mediocre because they lack context. The gap is **an AI-native workspace that deeply understands your specific product, team, and company context** and can assist with any PM task — from ideation to spec writing to safety evaluation to stakeholder communication — without ever leaving the flow state.

That's what Cursor did for code. That's what this would do for product management at a frontier AI company.

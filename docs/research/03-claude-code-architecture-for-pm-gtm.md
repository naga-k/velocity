# Claude Code Architecture for PM/GTM: How to Build It

---

## Why Claude Code (Not Cursor)

For a Claude hackathon, the framing shifts from "Cursor for PMs" to "Claude Code for PMs/GTM" — and this is actually a *stronger* concept:

1. **Claude Code is already becoming a general-purpose agent platform.** Anthropic themselves note it's "poorly named" — it's not just for coding, it's for general computer automation. PMs are already adopting it for PRDs, competitive analysis, and prototyping without writing code.

2. **The agent infrastructure already exists.** Subagents, MCP, Skills, Hooks — Claude Code has a complete orchestration layer. You're not building from scratch; you're composing existing primitives into a PM/GTM-specific experience.

3. **It's buildable at a hackathon.** A Cursor-like editor is a multi-year product. A set of Claude Code subagents + MCP integrations + Skills for PM/GTM workflows is buildable in a week.

4. **It aligns with the hackathon's thesis.** The Opus 4.6 hackathon values technical creativity and concrete applications. A PM/GTM agent system that demonstrates the 1M-token context window and multi-agent orchestration fits perfectly.

---

## Claude Code Building Blocks (Refresher)

| Component | What It Does | PM/GTM Application |
|-----------|-------------|-------------------|
| **Subagents** | Autonomous, specialized agents with their own context and tool permissions. Defined as Markdown + YAML frontmatter in `.claude/agents/`. | A "Research Agent," a "Spec Writer Agent," a "Stakeholder Update Agent," a "GTM Outreach Agent" — each with its own expertise and tools. |
| **MCP Servers** | Universal connectors to external tools and data sources. Standardized protocol — build once, connect anywhere. | Connect to Linear, Notion, Slack, Figma, Amplitude, Salesforce, Gong, Clay, HubSpot. Pull real data into every agent task. |
| **Skills** | Folders of instructions, scripts, and resources loaded dynamically when relevant. Like "training materials" for Claude. | A "PRD Writing" skill, a "Competitive Analysis" skill, a "GTM Playbook" skill — each encoding best practices and templates. |
| **Hooks** | Shell commands attached to lifecycle events. Enforce quality gates and trigger follow-up actions. | Auto-run a "spec reviewer" after a PRD is written. Auto-create Linear tickets after a meeting debrief. Auto-check safety considerations before publishing. |
| **CLAUDE.md** | Project-level context that persists across sessions. Architecture, conventions, team context. | Your product's roadmap context, team structure, naming conventions, safety frameworks, OKR definitions — always available to every agent. |
| **Persistent Memory** | Subagents can have a memory directory that survives across conversations. | Accumulated product knowledge: past decisions, user research insights, competitive intelligence, metric baselines. |

---

## Proposed Architecture: The Agent Team

Think of this as assembling a team of junior PM/GTM analysts, each specialized, coordinated by Claude Code as the orchestrator.

### The PM Agent Squad

```
┌─────────────────────────────────────────────────┐
│              CLAUDE CODE (Orchestrator)          │
│   CLAUDE.md = product context, team, OKRs       │
│   Memory = accumulated product knowledge         │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Research  │  │   Spec   │  │ Comms    │      │
│  │  Agent   │  │  Writer  │  │  Agent   │      │
│  │          │  │  Agent   │  │          │      │
│  │ MCP:     │  │ MCP:     │  │ MCP:     │      │
│  │ - Slack  │  │ - Notion │  │ - Slack  │      │
│  │ - Intercom│ │ - Linear │  │ - Email  │      │
│  │ - Amplitude│ │ - Figma │  │ - Notion │      │
│  │ - Web    │  │          │  │          │      │
│  │          │  │ Skills:  │  │ Skills:  │      │
│  │ Skills:  │  │ - PRD    │  │ - Exec   │      │
│  │ - Research│  │ - Safety │  │   update │      │
│  │   synthesis│ │   eval  │  │ - Team   │      │
│  │ - User   │  │ - Spec   │  │   update │      │
│  │   interview│ │   review│  │ - Customer│     │
│  │   analysis│  │         │  │   update │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Metrics  │  │ Roadmap  │  │ Meeting  │      │
│  │  Agent   │  │  Agent   │  │  Agent   │      │
│  │          │  │          │  │          │      │
│  │ MCP:     │  │ MCP:     │  │ MCP:     │      │
│  │ - Amplitude│ │ - Linear│  │ - Fireflies│    │
│  │ - Pendo  │  │ - Notion │  │ - Slack  │      │
│  │ - SQL    │  │ - Slack  │  │ - Linear │      │
│  │          │  │          │  │ - Notion │      │
│  │ Skills:  │  │ Skills:  │  │          │      │
│  │ - Metric │  │ - Priorit-│ │ Skills:  │      │
│  │   analysis│  │  ization│  │ - Action │      │
│  │ - A/B test│  │ - Depend-│ │   extraction│   │
│  │   interp │  │   ency  │  │ - Decision│     │
│  │          │  │   mapping│  │   logging │     │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │          HOOKS (Quality Gates)          │     │
│  │ - Post-spec: auto-review for gaps      │     │
│  │ - Post-meeting: auto-create tickets    │     │
│  │ - Pre-publish: safety check            │     │
│  │ - On-metric-change: alert if anomaly   │     │
│  └────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

### The GTM Agent Squad

```
┌─────────────────────────────────────────────────┐
│              CLAUDE CODE (Orchestrator)          │
│   CLAUDE.md = ICP, messaging, competitive intel  │
│   Memory = deal patterns, what's working         │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Prospect │  │ Outreach │  │  Deal    │      │
│  │ Research │  │  Agent   │  │ Intel    │      │
│  │  Agent   │  │          │  │  Agent   │      │
│  │          │  │ MCP:     │  │          │      │
│  │ MCP:     │  │ - Email  │  │ MCP:     │      │
│  │ - Clay   │  │ - LinkedIn│ │ - Gong   │      │
│  │ - Apollo │  │ - Slack  │  │ - Salesforce│    │
│  │ - Web    │  │          │  │ - HubSpot│      │
│  │ - LinkedIn│  │ Skills:  │  │          │      │
│  │          │  │ - Person-│  │ Skills:  │      │
│  │ Skills:  │  │   alization│ │ - Deal  │      │
│  │ - ICP    │  │ - Multi- │  │   scoring│      │
│  │   matching│  │   channel│  │ - Objection│    │
│  │ - Signal │  │   sequence│  │  handling│     │
│  │   scoring │  │          │  │ - Competitive│  │
│  │          │  │          │  │   positioning│   │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Content  │  │ Analytics│  │ Customer │      │
│  │  Agent   │  │  Agent   │  │ Success  │      │
│  │          │  │          │  │  Agent   │      │
│  │ MCP:     │  │ MCP:     │  │          │      │
│  │ - Notion │  │ - Amplitude│ │ MCP:    │      │
│  │ - CMS    │  │ - HubSpot│  │ - Intercom│     │
│  │ - Figma  │  │ - SQL    │  │ - Slack  │      │
│  │          │  │          │  │ - Notion │      │
│  │ Skills:  │  │ Skills:  │  │          │      │
│  │ - Blog   │  │ - Funnel │  │ Skills:  │      │
│  │   writing│  │   analysis│  │ - Churn │      │
│  │ - Case   │  │ - Attribution│ │ prediction│  │
│  │   study  │  │   modeling│  │ - Health│      │
│  │ - Launch │  │          │  │   scoring│      │
│  │   messaging│ │         │  │          │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │          HOOKS (Quality Gates)          │     │
│  │ - Pre-send: human review for outreach  │     │
│  │ - Post-call: auto-log + follow-up      │     │
│  │ - On-deal-update: refresh strategy     │     │
│  │ - Weekly: pipeline health report       │     │
│  └────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

---

## Same App or Different Apps?

### The Case for One Unified Platform

PM and GTM share more DNA than people realize:

- **User research ↔ Prospect research** — Both involve understanding people, their pain points, and their context. Same skill, different audience.
- **PRDs ↔ Sales enablement docs** — Both translate value propositions into structured artifacts. A feature spec and a competitive battlecard have the same bones.
- **Roadmap ↔ Pipeline** — Both are forward-looking plans that need constant reprioritization based on incoming signal.
- **Stakeholder updates ↔ Deal updates** — Both involve tailoring communication to different audiences.
- **Customer feedback synthesis ↔ Conversation intelligence** — Productboard and Gong do the same thing from different angles.

A unified platform would share the underlying agent primitives (MCP connections, memory, context) and offer role-specific "views" or "modes" — like how Figma serves both designers and developers with the same file.

### The Case for Separate Apps

- **Different tools** — PMs live in Linear/Notion/Figma. GTM lives in Salesforce/HubSpot/Gong/Clay. The MCP connections are different.
- **Different cadences** — PM work is weekly/quarterly cycles. GTM work is daily/hourly (pipeline moves fast).
- **Different sensitivity** — GTM involves sending messages to external people (prospects, customers). PM work is mostly internal. The "human in the loop" requirements are stricter for GTM.
- **Simpler GTM for initial adoption** — If the GTM is narrow (e.g., sell to PMs), the app only needs to solve PM problems. GTM features come later.

### Recommended Approach: Shared Core, Role-Specific Agents

Build a **shared Claude Code plugin/skill foundation** with:
- Common MCP connections (Slack, Notion, Google Docs)
- Shared memory layer (product context, company context)
- Shared quality-gate hooks

Then layer **role-specific agent packs** on top:
- `pm-agents/` — Research, Spec Writer, Roadmap, Metrics, Meeting, Comms
- `gtm-agents/` — Prospect Research, Outreach, Deal Intel, Content, Analytics, CS

This mirrors how Claude Code already works — you install different agents for different projects. A PM installs `pm-agents`, a GTM leader installs `gtm-agents`, and the shared foundation means insights flow between them.

---

## What to Build for the Hackathon

Given the time constraint, here's a realistic scope:

### MVP: 3 Agents + 2 MCP Connections + 1 Skill

**Agents:**
1. **Research Synthesizer** — Takes a topic (feature idea, competitor, market trend), pulls data from connected sources (Slack, Notion, web), and produces a structured research brief.
2. **Spec Writer** — Takes the research brief + a one-liner feature description, produces a PRD with user stories, requirements, success metrics, and safety considerations. Uses the PRD skill for best practices.
3. **Stakeholder Update Generator** — Takes Linear ticket status + Slack discussions + metrics, produces audience-tailored updates (exec summary, team detail, customer-facing).

**MCP Connections:**
1. **Slack** — Pull discussion context, post updates
2. **Linear** (or Notion) — Pull ticket status, create tickets from action items

**Skill:**
1. **PRD Best Practices** — A skill file encoding Anthropic-style PRD structure, safety evaluation sections, and eval criteria templates.

**Hooks:**
1. **Post-Spec Review** — After Spec Writer produces a PRD, automatically run a quality check (missing sections, undefined edge cases, safety gaps).

### Demo Flow

```
User: "I want to write a spec for adding MCP support to our mobile app"

→ Orchestrator delegates to Research Synthesizer
  → Pulls relevant Slack discussions about MCP + mobile
  → Pulls existing Notion docs about MCP architecture
  → Searches web for MCP best practices
  → Produces structured research brief

→ Orchestrator delegates to Spec Writer
  → Loads PRD skill for best practices
  → Ingests research brief
  → Produces full PRD with safety section
  → Hook triggers: auto-review flags 2 gaps

→ User reviews, approves

→ Orchestrator delegates to Stakeholder Update Generator
  → Produces 3 versions: exec summary, eng detail, customer preview
  → Posts exec summary to #leadership Slack channel
```

This demo showcases: multi-agent orchestration, MCP-powered real-data grounding, skill-based quality, hooks for automated review, and the 1M-token context window (loading extensive product context).

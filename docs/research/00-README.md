# Claude Code for PM/GTM — Hackathon Research Package

**Project:** An agent-powered PM and GTM workspace built on Claude Code's architecture (subagents, MCP, skills, hooks) for the "Built with Opus 4.6" hackathon.

**Core thesis:** The gap in the market isn't "AI that writes PRDs" — it's an agent-native workspace with deep, persistent understanding of your specific product context that orchestrates the full PM/GTM workflow end-to-end.

---

## Documents in This Folder

| # | Document | What's Inside |
|---|----------|--------------|
| 01 | [Original Cursor-for-PMs Research](./01-cursor-for-pms-original-research.md) | What Anthropic PMs do, their tools, what makes Cursor special, and 10 feature ideas for a PM equivalent. The original "Cursor for PMs" framing. |
| 02 | [Market Landscape](./02-market-landscape.md) | Competitive analysis of PM tool startups (ChatPRD, Productboard, Zeda) and GTM tool startups (Clay, Apollo, Gong). Their GTM strategies, what's working, market sizing, and the competitive landscape map showing where the opportunity sits. |
| 03 | [Claude Code Architecture](./03-claude-code-architecture-for-pm-gtm.md) | Why Claude Code > Cursor for the hackathon. Technical architecture using subagents + MCP + skills + hooks. PM agent squad and GTM agent squad diagrams. "Same app or different apps" analysis. Concrete hackathon MVP scope. |
| 04 | [User Stories & Workflows](./04-user-stories-and-workflows.md) | 6 detailed user stories with before/after workflows. PM persona (Sarah) and GTM persona (Marcus). Shows exact agent orchestration flows. Includes the PM-GTM bridge story showing unified platform value. |

---

## Key Insight

Everyone is building **point solutions** — a tool for PRDs, a tool for enrichment, a tool for call intelligence. The opportunity is the **upper-right quadrant**: an agent-first platform that orchestrates the full workflow across tools, grounded in persistent product context.

Clay is approaching this from the GTM side. Nobody has done it for PM. Nobody has unified both. Claude Code's agent architecture makes it possible to build the MVP in a hackathon week.

---

## Hackathon MVP (Buildable in a Week)

3 agents + 2 MCP connections + 1 skill + 1 hook:

- **Research Synthesizer Agent** — pulls context from Slack + Notion + web
- **Spec Writer Agent** — produces grounded PRDs using a best-practices skill
- **Stakeholder Update Agent** — generates audience-tailored comms from Linear + Slack
- **MCP:** Slack, Linear (or Notion)
- **Skill:** PRD best practices template
- **Hook:** Auto-review specs for gaps after generation

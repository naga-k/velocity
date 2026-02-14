# User Stories & Workflows

---

## PM Persona: Sarah, Senior PM at a Series B AI Startup

Sarah manages the developer platform. She juggles Linear tickets, Notion specs, Slack fires, Figma reviews, Amplitude dashboards, and weekly stakeholder meetings. She spends 60% of her time on context-gathering and communication — not on the strategic thinking she was hired for.

---

### Story 1: "From Idea to Spec in 30 Minutes"

**As a PM, I want to turn a rough feature idea into a grounded, reviewed spec without spending a full day on it.**

**Current workflow (4-6 hours):**
1. Open a blank Notion doc → stare at it
2. Search Slack for past discussions about the feature → 30 min of scrolling
3. Check Linear for related tickets and past attempts → copy-paste context
4. Look at Amplitude for relevant usage data → screenshot charts
5. Check competitor products → open 10 tabs
6. Write the PRD → 2-3 hours of drafting
7. Share for review → wait for async feedback → iterate

**Agent workflow (30 min):**
```
Sarah: "@research-agent pull everything we have on 'batch API
        processing' — Slack discussions, Linear tickets, Notion docs,
        and relevant Amplitude metrics"

Research Agent: [5 min] Returns a structured brief:
  - 3 Slack threads with key decisions highlighted
  - 4 related Linear tickets (2 closed, 2 open)
  - Existing Notion doc from 6 months ago (outdated but useful)
  - Usage data: 340 API users, 12% hit rate limits weekly
  - 2 competitor approaches (Stripe, OpenAI)

Sarah: "@spec-writer write a PRD for batch API processing. Use the
        research brief. Target audience: eng team + API customers."

Spec Writer Agent: [3 min] Produces full PRD:
  - Problem statement (grounded in the actual user data)
  - User stories (derived from real Slack complaints)
  - Technical requirements (referencing existing architecture docs)
  - Success metrics (baseline from Amplitude data)
  - Safety/abuse considerations
  - Open questions

[Hook auto-triggers: Spec Reviewer]
  - Flags: "No rollback plan defined"
  - Flags: "Rate limit section contradicts existing API docs"
  - Suggests: "Add enterprise tier pricing implications"

Sarah: Reviews, edits 3 sections, resolves flags → done.
```

**Time saved:** ~4 hours. But more importantly, the spec is *grounded in real data* — not Sarah's memory of a Slack thread from 3 weeks ago.

---

### Story 2: "Monday Morning Stakeholder Update"

**As a PM, I want to generate a weekly update that's tailored to each audience without writing 3 different versions.**

**Current workflow (1.5 hours every Monday):**
1. Open Linear → scan completed tickets → summarize
2. Open Slack → skim key threads → note highlights
3. Open Amplitude → check dashboards → note metric changes
4. Write exec update (2 paragraphs, high-level)
5. Write eng update (detailed, technical)
6. Write customer-facing changelog (if applicable)
7. Post each to the right Slack channel

**Agent workflow (10 min):**
```
Sarah: "@comms-agent generate my weekly update for the API Platform team.
        Cover Jan 27 - Feb 2."

Comms Agent:
  → Pulls Linear: 14 tickets completed, 3 blocked
  → Pulls Slack #api-platform: key discussion about auth changes
  → Pulls Amplitude: API calls up 8%, error rate down 0.3%
  → Generates 3 versions:

  [EXEC] 2 paragraphs — shipped auth improvements, API adoption
         growing 8% WoW, one risk flagged on enterprise migration

  [ENG] Detailed ticket breakdown, technical blockers, next sprint
        priorities, dependency callouts

  [CUSTOMER] Changelog entry — new batch endpoint, improved error
             messages, deprecated v1 auth (migration guide linked)

Sarah: Reviews each, tweaks exec framing, approves.
Agent: Posts to #leadership, #api-eng, #api-changelog
```

---

### Story 3: "What Did We Decide About X?"

**As a PM, I want to instantly recall past product decisions and their rationale without searching through 6 months of Slack history.**

**Current workflow (20-45 min per question):**
1. Search Slack → get 47 results, most irrelevant
2. Find the right thread → read 200 messages to reconstruct context
3. Check Notion → maybe someone documented it, maybe not
4. Ask a colleague → they half-remember → more Slack searching

**Agent workflow (30 seconds):**
```
Sarah: "What did we decide about rate limiting for enterprise
        customers? And why?"

Research Agent: [searches indexed Slack, Notion, Linear, meeting notes]

"On Nov 12, the team decided on tiered rate limits:
 - Standard: 100 req/min
 - Enterprise: 1000 req/min
 - Custom: negotiable via sales

 Rationale (from #api-design thread, Nov 12):
 - CTO wanted uniform limits for simplicity
 - Sales pushed back — 3 enterprise deals blocked by 100 req/min cap
 - Compromise: tiered approach, revisit in Q2 if <5% of enterprise
   customers use >500 req/min

 Related: Linear ticket API-847 (implement tiered limits) — shipped
 Dec 3. Amplitude shows 2 enterprise customers consistently at 800+
 req/min since launch.

 Sources: [Slack thread] [Notion doc] [Linear ticket] [Amplitude chart]"
```

This leverages **persistent memory** — the agent has been indexing product context over time and can recall it instantly with citations.

---

## GTM Persona: Marcus, Head of Growth at the Same Startup

Marcus runs a 4-person GTM team. They're trying to grow API platform adoption from 340 to 1,000 active users in 6 months. He splits time between outbound prospecting, content, partnerships, and analyzing what's working.

---

### Story 4: "Turn a Conference Lead List Into Personalized Outreach"

**As a GTM lead, I want to convert a list of conference contacts into personalized, relevant outreach without spending a week on research.**

**Current workflow (5-8 hours per 50 leads):**
1. Export list from badge scanner → messy CSV
2. Manually research each person → LinkedIn, company website, recent news
3. Segment by relevance → who actually needs an API platform?
4. Write personalized emails → try to reference something specific
5. Load into email tool → send sequences
6. Half the emails are generic anyway because step 2 took too long

**Agent workflow (45 min for 50 leads):**
```
Marcus: "@prospect-agent I have 50 leads from API World 2026.
         Enrich them, score by ICP fit, and draft outreach."

Prospect Research Agent:
  → Reads CSV
  → For each lead, pulls: company info, tech stack, recent funding,
    job title, LinkedIn activity, any existing relationship in HubSpot
  → Scores each lead against ICP (B2B SaaS, Series A+, API-heavy product)
  → Segments: 12 high-fit, 23 medium-fit, 15 low-fit

Outreach Agent:
  → For each high-fit lead, drafts personalized email referencing:
    - Their specific product (pulled from company website)
    - A relevant pain point (inferred from their tech stack)
    - A specific API Platform feature that addresses it
  → Queues in email tool

Marcus: Reviews top 12 emails. Edits 3 that feel off. Approves rest.
        Sends medium-fit leads a lighter-touch sequence.
```

---

### Story 5: "Weekly Pipeline Intelligence Briefing"

**As a GTM lead, I want to know what's *actually* happening in my pipeline without spending half a day in Salesforce.**

**Agent workflow:**
```
Marcus: "@analytics-agent give me the weekly GTM briefing"

Analytics Agent:
  → Pulls HubSpot: 8 new opportunities, 3 moved to demo, 1 closed-won
  → Pulls Gong: analyzed 12 sales calls this week
    - Top objection: "How does this compare to building in-house?"
    - Winning pattern: demos that start with the prospect's specific
      use case convert 3x better than generic product tours
  → Pulls email analytics: outreach response rate up to 14%
    (was 9% last week — the conference follow-ups are working)
  → Pulls Amplitude: 3 trial users approaching conversion threshold

  "Recommendation: The 'build vs. buy' objection appeared in 8/12
   calls. Consider creating a comparison calculator or ROI tool.
   Your conference outreach is outperforming cold by 55% — prioritize
   working the remaining medium-fit leads this week.

   3 trial users (Company A, B, C) are highly active — flag for
   sales outreach before their trial expires Friday."
```

---

### Story 6: "Bridge the PM-GTM Gap"

**As both a PM and GTM leader, I want product insights to flow into sales conversations and vice versa — automatically.**

This is where the unified platform shines:

```
[PM side]
Sarah's Research Agent discovers: "Enterprise customers are requesting
webhook support — 6 Intercom tickets this month, 3 Slack mentions,
and Gong flagged it in 4 sales calls."

→ Auto-creates a signal in the shared context:
  "Webhook support: high-demand signal (PM + GTM convergence)"

[GTM side]
Marcus's Outreach Agent picks up the signal:
→ Adds "webhook support on roadmap" to outreach messaging for
   prospects who match the enterprise ICP
→ Updates the competitive battlecard: "Unlike Competitor X,
   we're shipping webhook support in Q2"

[PM side again]
Sarah's Roadmap Agent: "Webhook support has been mentioned in 4 sales
calls (via Gong) and 6 support tickets (via Intercom). 2 enterprise
deals worth $X are partially blocked. Recommend prioritizing for Q2."

→ This insight was assembled *automatically* from signals that
  originally lived in 4 different tools across 2 different teams.
```

---

## Workflow Summary Table

| Story | Persona | Current Time | Agent Time | Key Agents Used | Key MCPs |
|-------|---------|-------------|------------|-----------------|----------|
| Idea → Spec | PM | 4-6 hrs | 30 min | Research, Spec Writer | Slack, Linear, Notion, Amplitude, Web |
| Weekly Update | PM | 1.5 hrs | 10 min | Comms | Linear, Slack, Amplitude |
| Decision Recall | PM | 20-45 min | 30 sec | Research (+ memory) | Slack, Notion, Linear |
| Conference Leads | GTM | 5-8 hrs | 45 min | Prospect Research, Outreach | Clay/Apollo, LinkedIn, HubSpot, Email |
| Pipeline Briefing | GTM | 3-4 hrs | 5 min | Analytics | HubSpot, Gong, Amplitude, Email |
| PM-GTM Bridge | Both | Never happens | Automatic | Shared memory + cross-team signals | All connected sources |

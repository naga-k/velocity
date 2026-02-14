# What Startup PMs (and GTM People) Actually Do & What Tools They Live In

This doc is practical. It's meant to answer: **what should I integrate with, and what workflows should I automate?**

---

## How PMs Spend Their Time

Real data from surveys and time-tracking studies:

| Activity | % of Time | What It Actually Looks Like |
|----------|-----------|----------------------------|
| **Meetings & alignment** | 50-75% | Standups, 1:1s with eng/design, stakeholder syncs, customer calls, sprint planning, roadmap reviews. This is the biggest time sink and the hardest to reduce. |
| **Writing** (specs, updates, emails) | 10-20% | PRDs, one-pagers, Slack messages, stakeholder updates, release notes, decision docs. Often squeezed into gaps between meetings. |
| **User/market research** | 5-15% | Customer interviews, reviewing support tickets, reading feedback, competitive analysis. Most PMs wish they spent more here. |
| **Data analysis** | 5-10% | Checking dashboards, pulling metrics for reviews, analyzing experiment results, building cases for prioritization. |
| **Backlog/prioritization** | 5-10% | Grooming tickets, writing acceptance criteria, triaging bugs, sequencing work. |
| **Strategy** | 5-10% | Roadmap planning, OKR setting, longer-term thinking. Often the first thing that gets sacrificed. |

At early-stage startups specifically, PMs also cover: QA, customer support, some marketing, some sales enablement, and sometimes writing code or building prototypes. The boundaries are blurry.

---

## The Three Phases (What Changes at Launch)

### Pre-Launch (Discovery/Build)
- Tons of **customer interviews** (5-10/week)
- **Competitor research** (what exists, what's the gap)
- **Spec writing** (PRDs, user stories, wireframe reviews)
- **Eng collaboration** (daily standups, design reviews, unblocking)
- **Prototype testing** (showing early builds to users, iterating)
- **Go-to-market prep** (positioning, messaging, launch plan)

**Tools they're in:** Notion/Google Docs (writing), Figma (design review), Slack (everything), Linear/Jira (tickets), Zoom/Google Meet (interviews), maybe Dovetail or spreadsheets (research notes)

### Launch
- **Cross-team coordination** (eng, design, marketing, sales all need to be in sync)
- **Real-time monitoring** (is it working? are things breaking?)
- **Crisis management** (rollback plans, hotfixes)
- **Comms** (internal updates, external announcements, customer messaging)
- **Metrics watching** (activation, errors, adoption curves)

**Tools they're in:** Slack (war room), Linear (bug tracking), Amplitude/Mixpanel (metrics), Twitter/social (reception), Intercom (support tickets), email (announcements)

### Post-Launch (Growth/Iterate)
- **Feedback synthesis** (what are users saying, what patterns emerge)
- **Metrics analysis** (retention, activation, feature adoption)
- **Iteration planning** (what to fix, what to build next)
- **Stakeholder updates** (board, execs, team)
- **Growth experiments** (A/B tests, onboarding tweaks)

**Tools they're in:** Amplitude/Mixpanel (analytics), Intercom/Zendesk (feedback), Notion (docs), Linear (backlog), Slack (everything), Loom (async updates)

---

## The PM Tool Stack (Ranked by How Much Time PMs Spend In Them)

### Tier 1: PMs Live Here (Daily, Hours/Day)

| Tool | Category | What PMs Do In It | Startup Popularity |
|------|----------|-------------------|-------------------|
| **Slack** | Communication | Everything. Discussions, decisions, fires, updates, standups. The #1 context source for any PM. | Universal |
| **Linear** | Issue tracking | Create tickets, groom backlog, track sprint progress, link to specs. | Dominant at <500 people. Near-parity with Jira at <50. |
| **Jira** | Issue tracking | Same as Linear but heavier. More common at scale. | 57.5% of devs. Dominant at 1000+. Most disliked tool though. |
| **Notion** | Knowledge base | Write PRDs, meeting notes, decision logs, roadmaps, research repos. The PM's "home base" doc. | 56% collaborative workspace share. Default at startups. |
| **Google Docs** | Writing | Collaborative spec writing, stakeholder docs, anything that needs comments/suggestions. | Still huge, especially for external-facing docs. |
| **Figma** | Design | Review designs, comment on mocks, participate in design critiques, reference during spec writing. | Standard for any company with designers. |

### Tier 2: PMs Check These Daily (Minutes/Day)

| Tool | Category | What PMs Do In It | Startup Popularity |
|------|----------|-------------------|-------------------|
| **Amplitude** | Product analytics | Check feature adoption, funnel metrics, retention curves. Pull data for roadmap prioritization. | Top pick for product analytics. |
| **Mixpanel** | Product analytics | Same as Amplitude. Some teams prefer the UI. | Strong alternative to Amplitude. |
| **Intercom** | Customer feedback | Read support tickets, spot patterns, sometimes respond directly at early stage. | Very common at startups for in-app messaging. |
| **Loom** | Async video | Record walkthroughs, ship async updates, explain complex decisions without a meeting. | Widely adopted for reducing meetings. |
| **Google Meet / Zoom** | Video calls | Customer interviews, team meetings, stakeholder calls. | Universal. |

### Tier 3: PMs Use These Weekly

| Tool | Category | What PMs Do In It | Startup Popularity |
|------|----------|-------------------|-------------------|
| **Miro / FigJam** | Whiteboarding | Brainstorming sessions, user journey mapping, workshop facilitation. | Common for remote teams. |
| **Dovetail** | Research repo | Tag and organize user interview transcripts, find patterns across research. | Growing, especially research-heavy teams. |
| **Hotjar / FullStory** | Session replay | Watch users struggle, identify UX problems, validate hypotheses. | Common at product-led companies. |
| **Google Sheets** | Spreadsheets | Prioritization frameworks, quick data analysis, budget tracking, launch checklists. | Everyone still uses spreadsheets. |
| **Confluence** | Documentation | More structured docs in Atlassian-ecosystem companies. | 35% of devs. Declining at startups. |

---

## The GTM Tool Stack (For When PM Overlaps with Go-to-Market)

At early-stage startups, the PM often IS the GTM team, or works hand-in-hand with founders doing sales. Here's what that stack looks like:

### Tier 1: Core GTM Tools

| Tool | Category | What GTM People Do In It | Notes |
|------|----------|--------------------------|-------|
| **HubSpot** | CRM | Track deals, manage contacts, run email campaigns, landing pages. Free tier is generous. | Default CRM for startups. |
| **Attio** | CRM (AI-native) | Relationship management with AI enrichment built in. Auto-enriches contacts. | Rising fast as an alternative to HubSpot for small teams. |
| **Salesforce** | CRM (enterprise) | Everything HubSpot does but heavier. | Appears once you hit Series B+ or enterprise sales. |
| **Apollo** | Prospecting + data | Find prospects, get emails/phones, run outreach sequences. 210M+ contacts. | Very popular as a one-stop-shop for early outbound. |
| **Clay** | Data enrichment + workflows | Enrich prospects from 130+ sources, build automated GTM workflows. | $3.1B valuation. The "new" GTM engineering platform. |

### Tier 2: Outreach & Engagement

| Tool | Category | What GTM People Do In It |
|------|----------|--------------------------|
| **Instantly / Lemlist / Smartlead** | Cold email | Run cold email sequences with deliverability management. |
| **LinkedIn (+ Sales Navigator)** | Social selling | Find prospects, send connection requests, engage with content. |
| **Gong** | Conversation intelligence | Record and analyze sales calls. Surface objections, winning patterns, deal risks. |
| **Calendly** | Scheduling | Let prospects book meetings. |
| **Loom** | Async video | Send personalized video messages to prospects. |

### Tier 3: Analytics & Content

| Tool | Category | What GTM People Do In It |
|------|----------|--------------------------|
| **Google Analytics / Plausible** | Web analytics | Track traffic, conversion funnels, campaign performance. |
| **Jasper / Copy.ai** | AI content | Generate marketing copy, blog posts, email sequences. |
| **Webflow / Framer** | Website | Build and iterate on marketing site. |
| **Typeform** | Surveys | Collect user feedback, lead qualification forms. |

---

## Integration Priority Map (What to Connect First)

If you're building a tool that helps PMs/GTM people, here's the order of integration priority based on where they spend time and what data matters most:

### Must-Have (Week 1)
1. **Slack** — This is where all the context lives. Decisions, discussions, complaints, celebrations. If your tool can read Slack, it knows 80% of what's happening.
2. **Linear or Jira** — The source of truth for what's being built, what's shipped, and what's blocked.
3. **Notion or Google Docs** — Where specs, meeting notes, and decisions are written down.

### High Priority (Week 2-3)
4. **Amplitude or Mixpanel** — Product metrics. Needed for any data-grounded output.
5. **Figma** — Design context. Needed to understand what's being built visually.
6. **Intercom or Zendesk** — Customer voice. Support tickets and feedback.

### GTM Extensions (Week 3-4)
7. **HubSpot or Salesforce** — Deal pipeline, customer data.
8. **Apollo or Clay** — Prospect data, enrichment.
9. **Gong** — Call transcripts, customer conversation intelligence.

### Nice-to-Have
10. **Google Calendar** — Meeting context, scheduling.
11. **Loom** — Video content, async updates.
12. **Fireflies / Otter** — Meeting transcripts.
13. **Dovetail** — Research repository.

---

## The Key Insight for Building This

The PM's day is fundamentally about **context assembly**. They spend 50-75% of their time in meetings not because they love meetings, but because that's how they gather and distribute context across the team. The remaining time is spent writing (turning context into artifacts) and checking data (grounding decisions in reality).

A tool that can **assemble context automatically** from the tools listed above — and then help the PM turn that context into artifacts (specs, updates, roadmaps, analyses) — would directly attack the biggest time sink in their day.

That's what your chat interface does. It sits on top of all these tools, pulls context on demand, and helps the PM produce outputs without the manual context-gathering step. The UI is just a chat because the hard part isn't the interface — it's the integrations and the context.

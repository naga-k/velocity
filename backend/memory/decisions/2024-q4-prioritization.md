# Q4 2024 Prioritization Decision

**Date:** October 15, 2024
**Decision:** Prioritize Dark Mode over Advanced Filtering
**Status:** Implemented

## Context

We had to choose between two feature requests for Q4:
1. Dark mode support (requested by 42% of users in feedback survey)
2. Advanced filtering for backlog views (requested by 18% of users)

## Decision

We decided to build Dark Mode first based on RICE scoring:

**Dark Mode:**
- Reach: 420 users (42% of 1000 monthly active)
- Impact: 3 (high - quality of life improvement)
- Confidence: 90%
- Effort: 2 weeks
- **RICE Score:** 567

**Advanced Filtering:**
- Reach: 180 users (18% of 1000)
- Impact: 2 (medium - workflow improvement)
- Confidence: 70%
- Effort: 3 weeks
- **RICE Score:** 84

## Reasoning

- 5x higher RICE score for Dark Mode
- Dark mode addresses eye strain complaints (health/accessibility)
- Filtering can be added incrementally later
- Dark mode was blocking enterprise deal (Fortune 500 company requirement)

## Outcome

- Dark mode shipped in 2 weeks as estimated
- 65% adoption rate within first month
- Enterprise deal closed (+$250K ARR)
- Advanced filtering moved to Q1 2025 roadmap

## Sources

- User feedback survey: [link-to-survey](https://example.com/survey)
- RICE scoring doc: [link-to-doc](https://example.com/rice)
- Enterprise customer conversation: Slack thread #enterprise-deals

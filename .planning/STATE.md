---
status: planning
phase: 1
milestone: 1
---

# State — Startup Scouting Pipeline

## Current Position
- **Milestone:** 1 — Scouting Pipeline v1.0
- **Phase:** 1 — MVP DealPad Pipeline End-to-End
- **Status:** Not Started
- **LastActivity:** 2026-04-10

## Progress
| Phase | Name | Status |
|-------|------|--------|
| 1 | MVP — DealPad Pipeline | Not Started |
| 2 | Scout Framework + Simple Parsers | Blocked by Phase 1 |
| 3 | Auth-Based & Complex Parsers | Blocked by Phase 2 |
| 4 | Research Enrichment Pipeline | Blocked by Phase 2 |
| 5 | Full Scoring & Report Suite | Blocked by Phase 4 |
| 6 | Delivery & Automation | Blocked by Phase 5 |
| 7 | Advanced Features & Polish | Blocked by Phase 3 |

## Decisions
- 2026-04-10: OpenRouter API via openai SDK (with base_url override) — matches MVP plan, official SDK v0.8.1 available as upgrade path
- 2026-04-10: Reddit requires OAuth2 (no free anonymous access) — planned for Phase 3
- 2026-04-10: Product Hunt requires GraphQL API auth — planned for Phase 3
- 2026-04-10: YC Companies via yc-oss/api (community Algolia endpoint) — planned for Phase 3

---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: "### Phase 1: MVP — DealPad Pipeline End-to-End"
status: planning
last_updated: "2026-04-10T12:09:25.431Z"
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 6
  completed_plans: 6
  percent: 100
---

# State — Startup Scouting Pipeline

## Current Position

Phase: 1 (MVP — DealPad Pipeline End-to-End) — EXECUTING
Plan: Not started

- **Milestone:** 1 — Scouting Pipeline v1.0
- **Phase:** 2
- **Status:** Ready to plan
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
- [Phase 01]: api_key fallback to 'not-set' in AsyncOpenAI so lib/llm.py imports cleanly without env var set
- [Phase 01]: include_niches uses 29 entries from docs/MVP_Plan.md (authoritative) not 26 as mentioned in plan task description
- [Phase 01]: Round extraction uses per-line regex scan rather than fixed 'Раунд:' prefix — handles format variants in actual DealPad export
- [Phase 01]: matches_niches uses word-boundary regex not simple substring — prevents AI matching railway/wait/detail (Pitfall 5)
- [Phase 01]: score_one_idea returns None on validation failure — lets asyncio.gather collect all results cleanly
- [Phase 01]: Shortlist re-scans all 1_ideas/ after writing rather than accumulating in-memory — handles idempotent re-runs where some ideas were pre-scored
- [Phase 01]: compute_weighted_score accepts both plain numeric scores and {score, rationale} dicts
- [Phase 01]: determine_verdict sorts thresholds dict descending by value — config-driven, not hardcoded
- [Phase 01-05]: LLM-first digest with manual fallback: tries light model first, falls back to build_digest_manually() if result < 200 chars
- [Phase 01-05]: load_dotenv() placed at module level in run_pipeline.py before pipeline imports to ensure env vars loaded before lib/llm.py reads them
- [Phase 01]: YAML string keys must be quoted in scoring_formula.yaml — PyYAML 1.1 coerces bare yes/no to booleans, breaking formula dict lookups
- [Phase 01-06]: LLM classification failures produce review_needed=True with is_tech=True/sector_match=partial fallback — ideas pass through to scoring, never false-archived
- [Phase 01-06]: Round size is invest_formula FACTOR (round_fit: in_range/close/far) not eligibility gate — invest_eligible computed from is_tech + sector_match only
- [Phase 01-06]: All shortlist thresholds unified in config/scoring_formula.yaml — deep_research and digest_generator read from config, no hardcoded values

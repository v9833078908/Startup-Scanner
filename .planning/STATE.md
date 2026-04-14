---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: "### Phase 1: MVP — DealPad Pipeline End-to-End"
status: executing
last_updated: "2026-04-14T11:13:01.519Z"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 14
  completed_plans: 11
  percent: 79
---

# State — Startup Scouting Pipeline

## Current Position

Phase: 02 (deep-research-pipeline-quality-upgrade) — EXECUTING
Plan: 1 of 3

- **Milestone:** 1 — Scouting Pipeline v1.0
- **Phase:** 1 complete, Phase 2+3 ready to plan
- **Status:** Executing Phase 02
- **LastActivity:** 2026-04-13

## Progress

| Phase | Name | Status |
|-------|------|--------|
| 1 | MVP — DealPad Pipeline | Complete (11 plans) |
| 2 | Multi-Source + Delivery | Ready to plan |
| 3 | Research Quality + Architecture | Ready to plan (parallel with 2) |
| 4 | Production Polish | Blocked by 2+3 |

## Accumulated Context

### Roadmap Evolution

- 2026-04-10: Original 7-phase roadmap created
- 2026-04-13: Consolidated to 4 phases (merged old 2+3+6 → Phase 2, old 4+5 → Phase 3, old 7 → Phase 4)
- 2026-04-13: Plans 01-08..01-11 added to Phase 1 (invest/build track split + web search abstraction)

### Pipeline Run Results

- Run 2 (01-06): 424 → 306 → 191 shortlisted (63%) — build score inflated
- Run 3 (01-07): 424 → 307 → 271 research → 206 analyzed — research gate too permissive (76% pass)
- Run 4 (01-08): 424 → 307 → route: invest=145, build=26, both=33, skip=103 — build_candidate 78%→19%

### P1 Bugs Fixed (2026-04-13)

- llm.py: returns None on JSON parse failure (was returning raw string → garbage in research files)
- deep_analysis.py: reads invest_research.md/build_research.md (was reading only legacy web_research.md)
- invest/build_research.py: writes "(LLM synthesis failed)" instead of str(None)
- triage.py: uses make_slug() for research_list (was using file_path.stem with date prefix → 0 matched)

## Decisions

- 2026-04-10: OpenRouter API via openai SDK (base_url override)
- 2026-04-10: DDG default search with Sonar fallback, Exa for production
- 2026-04-10: Search abstraction layer: all research modules import web_search()
- [Phase 01]: .replace() not .format() for prompts (literal JSON braces)
- [Phase 01]: Round size = scoring FACTOR, not eligibility gate
- [Phase 01]: unknown founder = neutral (0), not negative (-1)
- [Phase 01]: invest_score/build_score only in 3_analysis/ (deferred from triage)
- [Phase 01]: LLM classification failures → review_needed=True with safe fallback
- [Phase 01-08]: build_candidate requires replicability easy/medium + stack_fit
- [Phase 01-08]: route field (invest/build/both/skip) determines pipeline track
- [Phase 01-08]: deep_analysis configurable per track: build=on, invest=off, invest_top_n=20

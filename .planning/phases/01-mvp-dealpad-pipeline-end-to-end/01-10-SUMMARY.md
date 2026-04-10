---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: 10
subsystem: pipeline-orchestrator
tags: [dual-track, pipeline-wiring, invest-build-fork, orchestrator]

requires:
  - phase: 01-mvp-dealpad-pipeline-end-to-end
    plan: 08
    provides: "triage with route field and route_distribution"
  - phase: 01-mvp-dealpad-pipeline-end-to-end
    plan: 09
    provides: "invest_research, build_research, invest_gate, build_gate modules"
provides:
  - "9-stage dual-track pipeline orchestrator in run_pipeline.py"
  - "Route-based fork after triage: invest/build/both/skip"
  - "Merged analysis-ready slugs from dual gates for deep_analysis"
  - "SCHEMA.md with full dual-track gate contracts"
affects: [run_pipeline.py, SCHEMA.md]

tech-stack:
  added: []
  patterns:
    - "_derive_route() fallback for when route field not yet set by triage"
    - "dict.fromkeys() for order-preserving deduplication of analysis-ready slugs"

key-files:
  created: []
  modified:
    - run_pipeline.py
    - SCHEMA.md

key-decisions:
  - "_derive_route() falls back to invest_priority + build_candidate when route field is absent -- enables parallel plan execution without strict merge ordering"
  - "Legacy deep_research and research_gate imports kept but no longer called in main() -- backward compat for any direct imports"
  - ".env.example not modified -- EXA_API_KEY already present from Plan 09"

patterns-established:
  - "Dual-track fork pattern: split research_list by route, run both tracks, merge analysis-ready"
  - "Route derivation fallback: prefer explicit route field, fall back to computed route"

requirements-completed: [R6, R8]

duration: 3min
completed: 2026-04-10
---

# Phase 01 Plan 10: Dual-Track Pipeline Wiring Summary

**Rewired run_pipeline.py from 7-stage unified funnel to 9-stage dual-track (invest/build) pipeline with route-based forking after triage and merged analysis-ready output**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-10T15:00:51Z
- **Completed:** 2026-04-10T15:03:48Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote run_pipeline.py main() from 7-stage to 9-stage dual-track pipeline
- After triage, research_list is split into invest_slugs and build_slugs based on route field
- Stages 4-5 run invest_research and build_research (Exa-powered) on their respective slug lists
- Stages 6-7 run invest_gate and build_gate for analysis readiness checks
- Stage 8 merges and deduplicates analysis-ready slugs from both gates for deep_analysis
- Added _derive_route() helper that uses route field when available, falls back to invest_priority + build_candidate
- Updated STRIP_FIELDS with all new dual-track fields (replicability, cis_gap_likelihood, stack_fit, route, invest_analysis_ready, build_analysis_ready, cis_gap_confirmed, replicable_confirmed, oss_base_available, market_demand_signals)
- Updated SCHEMA.md with dual-track gate contracts and new research file types

## Task Commits

Each task was committed atomically:

1. **Task 1: Update run_pipeline.py with dual-track fork** - `bd42877` (feat)
2. **Task 2: Update SCHEMA.md with new fields** - `8e67e6a` (feat)

## Files Created/Modified
- `run_pipeline.py` - 9-stage dual-track pipeline with route-based forking, _derive_route() fallback, dual-track summary logging, updated STRIP_FIELDS and argparse description
- `SCHEMA.md` - Added invest_analysis_ready, build_analysis_ready, cis_gap_confirmed, replicable_confirmed, oss_base_available, market_demand_signals fields; added invest_research.md, build_research.md, gate_invest.md, gate_build.md file descriptions and contracts; legacy analysis_ready backward compat note

## Decisions Made
- _derive_route() falls back to invest_priority + build_candidate when route field is absent, enabling parallel plan execution without strict merge ordering
- Legacy deep_research and research_gate imports kept for backward compat but no longer called in main()
- .env.example not modified -- EXA_API_KEY already present from Plan 09

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Route field not yet present in triage.py on this branch**
- **Found during:** Task 1
- **Issue:** Plan 08 (triage build signals + route computation) executes in parallel and has not been merged yet. triage.py on this branch does not set `route` or return `route_distribution`.
- **Fix:** Added `_derive_route()` helper that checks for explicit `route` field first, then falls back to computing route from `invest_priority` + `build_candidate`. Also computes route_dist inline when triage doesn't provide it.
- **Files modified:** run_pipeline.py
- **Commit:** bd42877

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None -- no external service configuration required beyond existing EXA_API_KEY.

## Next Phase Readiness
- Pipeline is fully wired as 9-stage dual-track funnel
- Once Plan 08 merges, route field will be used directly (no fallback needed)
- Pipeline handles invest-only, build-only, both, and skip routing correctly
- --reset cleans all new fields for clean re-runs

## Self-Check: PASSED

All 3 modified/verified files present on disk. Both task commits (bd42877, 8e67e6a) verified in git log. SUMMARY.md created at correct path.

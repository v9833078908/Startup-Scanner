---
phase: 08-invest-build-track-split
plan: 01
subsystem: pipeline
tags: [triage, routing, build-signals, replicability, dual-track]

requires:
  - phase: 01-mvp-dealpad-pipeline-end-to-end
    provides: "triage.py with invest_priority + build_candidate, triage prompt (5 questions), triage config"
provides:
  - "Extended triage with 8-question prompt (3 build signals: replicability, cis_gap_likelihood, stack_fit)"
  - "compute_route() function returning invest/build/both/skip"
  - "Tighter build_candidate requiring replicability in (easy/medium) AND stack_fit=true"
  - "route field in idea frontmatter for downstream pipeline forking"
affects: [08-02-PLAN, 08-03-PLAN, pipeline-orchestrator]

tech-stack:
  added: []
  patterns:
    - "Route computation as pure function from invest_priority + build_candidate"
    - "LLM output validation with safe defaults (replicability defaults to 'hard')"

key-files:
  created: []
  modified:
    - prompts/triage.md
    - config/triage.yaml
    - pipeline/triage.py
    - SCHEMA.md

key-decisions:
  - "replicability defaults to 'hard' on invalid LLM output -- conservative default reduces false build candidates"
  - "Route computed from invest_priority + build_candidate, not from raw LLM signals -- keeps routing logic deterministic and testable"
  - "Previously-triaged ideas in research_list check route field (not invest_priority/build_candidate separately) -- single source of truth"

patterns-established:
  - "Route field as single routing decision: invest/build/both/skip replaces multi-field checks"
  - "Build candidate tightening pattern: add LLM signals to config requirements without changing invest-side logic"

requirements-completed: [R5]

duration: 3min
completed: 2026-04-10
---

# Phase 8 Plan 1: Triage Build Signals and Route Computation Summary

**Extended triage to 8 questions with replicability/cis_gap/stack_fit build signals and route computation (invest/build/both/skip) for dual-track pipeline forking**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-10T14:40:10Z
- **Completed:** 2026-04-10T14:43:49Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Extended triage prompt from 5 to 8 questions with build-specific signals (replicability, cis_gap_likelihood, stack_fit)
- Tightened build_candidate definition: now requires replicability in (easy/medium) AND stack_fit=true, expected to reduce pass rate from ~78% to ~20-30%
- Added compute_route() function that maps invest_priority + build_candidate to a single route field (invest/build/both/skip)
- Updated SCHEMA.md with all new frontmatter fields

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend triage prompt and config with build signals** - `e9182c6` (feat)
2. **Task 2: Update triage.py with route computation and tighter build_candidate** - `ee0d13d` (feat)

## Files Created/Modified
- `prompts/triage.md` - Added 3 new questions (replicability, cis_gap_likelihood, stack_fit), updated examples to 8 keys, added 4th build-focused example
- `config/triage.yaml` - Added replicability and stack_fit to build_candidate_requires, added route_rules documentation section
- `pipeline/triage.py` - Added 3 new fields to REQUIRED_KEYS, validation for replicability, compute_build_candidate now 3-param with tighter logic, added compute_route(), run_triage() writes route and tracks route_distribution
- `SCHEMA.md` - Documented replicability, cis_gap_likelihood, stack_fit, route fields in 1_ideas/ schema

## Decisions Made
- replicability defaults to "hard" on invalid LLM output -- conservative default reduces false build candidates
- Route computed deterministically from invest_priority + build_candidate, not from raw LLM signals
- Previously-triaged ideas use route field for research_list inclusion (single source of truth)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Route field enables Plans 02-03 to fork pipeline into invest-specific and build-specific research/gate tracks
- compute_route() is exported and testable by downstream modules
- Config-driven build_candidate thresholds can be tuned without code changes

## Self-Check: PASSED

All 4 modified files verified present. Both task commits (e9182c6, ee0d13d) verified in git log. SUMMARY.md created.

---
*Phase: 08-invest-build-track-split*
*Completed: 2026-04-10*

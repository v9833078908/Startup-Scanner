---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: 07
subsystem: pipeline
tags: [triage, research-gate, binary-signals, anti-bias, llm, funnel]

# Dependency graph
requires:
  - phase: 01-06
    provides: "LLM prefilter classification with sector_match, is_tech, product_type"
provides:
  - "pipeline/triage.py — Stage 3 binary triage with invest_priority and build_candidate"
  - "pipeline/research_gate.py — Stage 4.5 rare signal detection and analysis readiness gate"
  - "prompts/triage.md — calibrated triage prompt with base-rate anchors and few-shot examples"
  - "prompts/research_gate.md — build rare signals + invest evidence check prompt"
  - "config/triage.yaml — triage thresholds and research gate signal config"
  - "7-stage pipeline: parse -> prefilter -> triage -> research -> research_gate -> analysis -> digest"
affects: [scoring, digest, research, analysis]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Binary evidence signals instead of numeric scales at triage stage"
    - "Anti-bias LLM prompting with base-rate anchors and negative-first framing"
    - "Research gate as funnel narrowing between research and expensive analysis"
    - "Rare build signal detection only after research enrichment"

key-files:
  created:
    - "pipeline/triage.py"
    - "pipeline/research_gate.py"
    - "config/triage.yaml"
    - "prompts/triage.md"
    - "prompts/research_gate.md"
  modified:
    - "pipeline/deep_research.py"
    - "pipeline/digest_generator.py"
    - "run_pipeline.py"
    - "SCHEMA.md"

key-decisions:
  - "invest_priority from 4 binary signal count (sector_fit, round_in_range, has_product_evidence, has_founder_signal) — not numeric LLM scores"
  - "Unknown founder data is neutral (0 signals), not negative — absence of evidence is not evidence of absence"
  - "build_candidate is type-level filter only; rare build signals (ru_gap, oss, cross_sell) detected at research gate after enrichment"
  - "Research gate: invest needs 2/3 evidence types OR any 1 rare build signal to be analysis-ready"
  - "Deleted scoring_formula.yaml, quick_score.py, quick_score.md — invest_score/build_score now only exist in 3_analysis/"

patterns-established:
  - "Anti-bias prompting: base-rate anchors ('Most startups 60-70% will have NO evidence'), negative-first answer framing, few-shot calibration examples"
  - "Funnel narrowing: each stage answers a simpler question than the next (worth looking at? -> worth researching? -> worth analyzing?)"
  - "Signal-based priority: count binary yes/no signals rather than compute weighted numeric scores from thin data"

requirements-completed: [R4, R5]

# Metrics
duration: 8min
completed: 2026-04-10
---

# Phase 01 Plan 07: 5-Stage Triage Funnel Summary

**Binary triage with anti-bias LLM prompting replaces formula scoring; research gate narrows funnel from ~60 to ~20 analysis-ready startups**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-10T13:11:13Z
- **Completed:** 2026-04-10T13:19:21Z
- **Tasks:** 4
- **Files modified:** 10 (5 created, 3 modified, 3 deleted)

## Accomplishments
- Replaced numeric formula scoring (invest_score/build_score at triage) with binary evidence signals (invest_priority high/medium/low + build_candidate bool)
- Created calibrated triage prompt with anti-bias techniques: base-rate anchors, negative-first framing, 3 few-shot examples
- Added research gate (Stage 4.5) that evaluates enriched data for analysis readiness and detects rare build signals
- Upgraded pipeline from 6 to 7 stages with research_gate between research and analysis

## Task Commits

Each task was committed atomically:

1. **Task 1: New configs and prompts** - `772103b` (feat)
2. **Task 2: pipeline/triage.py** - `7571f76` (feat)
3. **Task 3: pipeline/research_gate.py** - `35b7f11` (feat)
4. **Task 4: Update downstream, delete old files** - `316f4f2` (feat)

## Files Created/Modified
- `config/triage.yaml` - Invest priority thresholds, build candidate requires, research gate signal config
- `prompts/triage.md` - Calibrated triage prompt with anti-bias anchors and few-shot examples
- `prompts/research_gate.md` - Build rare signals + invest evidence check prompt with negative defaults
- `pipeline/triage.py` - Stage 3 binary triage: invest_priority, build_candidate, no numeric scores
- `pipeline/research_gate.py` - Stage 4.5: evaluate enriched data, detect rare build signals, decide analysis readiness
- `pipeline/deep_research.py` - Reads invest_priority/build_candidate instead of invest_score/build_score
- `pipeline/digest_generator.py` - Uses triage stats instead of scoring_formula.yaml thresholds
- `run_pipeline.py` - 7-stage pipeline chain with research_gate, updated --reset field stripping
- `SCHEMA.md` - Documents triage fields, gate.md contract, notes invest_score only in 3_analysis/
- `pipeline/quick_score.py` - DELETED
- `prompts/quick_score.md` - DELETED
- `config/scoring_formula.yaml` - DELETED

## Decisions Made
- invest_priority from 4 binary signal count (not numeric LLM scores) -- simple, transparent, auditable
- Unknown founder = 0 signals (neutral), not -1 (negative) -- data absence is not negative evidence
- build_candidate is type-level filter only at triage; rare build signals come at research gate after enrichment
- Research gate threshold: invest needs 2/3 evidence types OR any 1 rare build signal
- Deleted all old scoring infrastructure (formula, quick_score, prompt) to prevent confusion

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 7-stage pipeline is structurally complete for end-to-end runs
- Ready for full pipeline run with --reset to validate funnel ratios
- invest_score/build_score now properly deferred to Stage 6 (deep_analysis) where evidence exists

## Self-Check: PASSED

- All 9 expected files found
- All 3 deleted files confirmed absent
- All 4 task commits verified (772103b, 7571f76, 35b7f11, 316f4f2)

---
*Phase: 01-mvp-dealpad-pipeline-end-to-end*
*Completed: 2026-04-10*

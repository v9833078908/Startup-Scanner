---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: "06"
subsystem: pipeline
tags: [llm-classification, scoring-formula, prefilter, quick-score, yaml, openrouter]

requires:
  - phase: 01-01
    provides: DealPad parser and 1_ideas/ schema
  - phase: 01-02
    provides: lib/llm.py call_llm/load_prompt, lib/utils.py load_idea/save_idea
  - phase: 01-03
    provides: pipeline/deep_research.py, pipeline/deep_analysis.py, pipeline/digest_generator.py

provides:
  - LLM-based sector classification (is_tech, sector, sector_match, product_type, b2b_b2c)
  - Two-track eligibility system (invest_eligible, build_eligible)
  - Formula-computed invest_score and build_score from structured LLM answers
  - config/scoring_formula.yaml as single source of truth for all shortlist thresholds
  - Full pipeline --reset that clears all downstream state

affects:
  - phase-02-scout-framework (will produce ideas consumed by this prefilter)
  - phase-05-scoring (deep scoring builds on invest_eligible/build_eligible tags)
  - phase-06-delivery (digest uses config-driven thresholds)

tech-stack:
  added: [pyyaml (scoring_formula.yaml), asyncio.gather for concurrent LLM classification]
  patterns:
    - formula-based scoring (config-driven, not LLM-generated numbers)
    - graceful LLM failure with pass-through fallback (review_needed flag)
    - quoted YAML string keys to prevent PyYAML 1.1 boolean coercion of yes/no

key-files:
  created:
    - prompts/classify.md
    - config/scoring_formula.yaml
  modified:
    - config/filters.yaml
    - prompts/quick_score.md
    - pipeline/prefilter.py
    - pipeline/quick_score.py
    - pipeline/deep_research.py
    - pipeline/digest_generator.py
    - run_pipeline.py
    - SCHEMA.md

key-decisions:
  - "YAML keys for yes/no/true/false must be quoted in scoring_formula.yaml — PyYAML 1.1 coerces bare yes/no to booleans, breaking dict lookup"
  - "LLM classification failures produce review_needed=True + is_tech=True/sector_match=partial fallback — ideas pass through, never false-archived"
  - "Round size is invest_formula FACTOR (0/1/2 pts via round_fit) not eligibility gate — invest_eligible computed from is_tech + sector_match only"
  - "product_type=unknown passes build_eligible — don't reject on classification failure"
  - "All shortlist consumers (deep_research, digest_generator) read thresholds from config/scoring_formula.yaml — single source of truth"
  - "--reset strips 17 scoring/classification fields from all idea frontmatter and clears 2_research/, 3_analysis/, digests/"

patterns-established:
  - "Formula scoring pattern: LLM answers structured questions, Python computes score — never ask LLM for a number"
  - "Graceful failure pattern: async LLM classify_one always returns a dict (fallback on failure), never None"
  - "Config-driven thresholds: all consumers import from scoring_formula.yaml, no hardcoded >= 6 or >= 8"
  - "Idempotency via classification_status field: prefilter skips ideas already classified"

requirements-completed: [R4, R5]

duration: 5min
completed: "2026-04-10"
---

# Phase 1 Plan 06: Improved Pre-filter and Quick Score Summary

**LLM sector classification replaces keyword matching, formula-computed invest/build scores replace opaque 1-10 LLM ratings, with graceful failure handling and config-driven thresholds across all pipeline consumers.**

## Performance

- **Duration:** ~5 minutes
- **Started:** 2026-04-10T12:02:33Z
- **Completed:** 2026-04-10T12:07:30Z
- **Tasks:** 4
- **Files modified:** 9

## Accomplishments

- Replaced keyword-based include_niches filter (rejected 259/424 startups) with LLM classification — semantic sector detection with graceful fallback for LLM failures
- Replaced opaque LLM-generated 1-10 scores (83% of startups scored >=6) with formula-computed scores from structured answers — every point traceable to a factor
- Unified all shortlist thresholds in config/scoring_formula.yaml — deep_research.py and digest_generator.py now read from config instead of having hardcoded values

## Task Commits

1. **Task 1: New configs and prompts** - `9093dc2` (feat)
2. **Task 2: Rewrite pipeline/prefilter.py** - `fd19724` (feat)
3. **Task 3: Rewrite pipeline/quick_score.py** - `2d7008b` (feat)
4. **Task 4: Update downstream consumers, SCHEMA.md, --reset** - `7811a76` (feat)

## Files Created/Modified

- `prompts/classify.md` — new LLM sector/product classifier (is_tech, sector, sector_match, product_type, b2b_b2c)
- `config/scoring_formula.yaml` — formula weights for invest/build scores; shortlist thresholds as single source of truth
- `config/filters.yaml` — removed include_niches and invest_round_min/max; kept hard rejects only
- `prompts/quick_score.md` — rewritten to 9 structured questions; LLM no longer outputs invest_score/build_score
- `pipeline/prefilter.py` — full rewrite: two-stage (hard reject + async LLM classify); graceful failure with review_needed
- `pipeline/quick_score.py` — full rewrite: structured questions + compute_score() formula; round_fit as scoring factor
- `pipeline/deep_research.py` — reads invest_threshold/build_threshold from config/scoring_formula.yaml
- `pipeline/digest_generator.py` — load_shortlist_thresholds() helper; all hardcoded >= 6 / >= 8 replaced
- `run_pipeline.py` — --reset flag, async main(), do_reset() clears all downstream state
- `SCHEMA.md` — documents all new fields including classification_status, review_needed, round_fit, formula-computed scores

## Decisions Made

- **YAML boolean coercion fix:** PyYAML 1.1 parses bare `yes`/`no` as `True`/`False`. All string keys in scoring_formula.yaml are quoted to preserve them as strings. Discovered during Task 3 verification when perfect invest score returned 8 instead of 10.
- **Fallback is pass-through, not reject:** On LLM classification failure, defaults are is_tech=True/sector_match=partial so ideas flow to scoring. False rejects are worse than false positives at this stage.
- **Round as factor, not gate:** invest_eligible ignores round_usd entirely. A $50M startup can still be invest_eligible if sector matches — round_fit just gives 0 points in the formula.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PyYAML 1.1 boolean coercion of yes/no in scoring_formula.yaml**
- **Found during:** Task 3 verification (`compute_score` returned 8 for perfect answers, expected 10)
- **Issue:** YAML inline dicts `{yes: 2, partial: 1, no: 0}` — PyYAML 1.1 parses bare `yes` as `True` and `no` as `False`, so lookup of string `"yes"` returned 0 instead of 2
- **Fix:** Rewrote scoring_formula.yaml with explicit quoted block keys (`"yes": 2`, `"no": 0`) for all string-valued keys
- **Files modified:** config/scoring_formula.yaml
- **Verification:** `compute_score(perfect_answers, invest_formula) == 10` confirmed; all 4 test cases pass
- **Committed in:** `2d7008b` (Task 3 commit, included the YAML fix alongside quick_score.py)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Essential correctness fix. Without it, sector_match "yes" scored 0 instead of 2, breaking the entire formula. No scope creep.

## Issues Encountered

None beyond the YAML boolean coercion bug (documented above as deviation).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Pipeline pre-filter and quick score are fully rewritten and verified
- All consumers (deep_research, digest_generator) read thresholds from config
- Full --reset available for clean re-runs during testing
- Ready for Phase 2 (Scout Framework + parsers) — new ideas will flow through the improved two-track classify/score pipeline

---
*Phase: 01-mvp-dealpad-pipeline-end-to-end*
*Completed: 2026-04-10*

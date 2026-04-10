---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: "03"
subsystem: pipeline
tags: [llm, openrouter, async, scoring, frontmatter, pipeline]

dependency_graph:
  requires:
    - lib/llm.py
    - lib/utils.py
    - prompts/quick_score.md
    - pipeline/prefilter.py
  provides:
    - pipeline/quick_score.py
  affects:
    - run_pipeline.py (calls run_quick_score)
    - pipeline/deep_analysis.py (reads shortlist from 1_ideas/)

tech_stack:
  added: []
  patterns:
    - Async score_one_idea with prompt template variable substitution
    - asyncio.gather with return_exceptions=True for batch LLM calls
    - Idempotency via "invest_score" in post.metadata check before scoring
    - Shortlist built by re-scanning all passed ideas after scoring round
    - Score clamping with max(1, min(10, int(score)))

key_files:
  created:
    - pipeline/quick_score.py
  modified: []

key_decisions:
  - "score_one_idea returns None (not raises) on validation failure — lets gather collect all results cleanly without poisoning the batch"
  - "Shortlist re-scans all 1_ideas/ after writing rather than accumulating in-memory — handles idempotent re-runs where some ideas were already scored in a previous run"

requirements-completed: [R5]

duration: 5min
completed: "2026-04-10"
---

# Phase 1 Plan 3: LLM Quick Scoring Summary

**Async OpenRouter scoring stage that sends each pre-filtered idea to the light model, writes 6 scores + rationale fields to YAML frontmatter, and returns a shortlist of invest_score >= 6 OR build_score >= 6 ideas**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-10T09:24:00Z
- **Completed:** 2026-04-10T09:29:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `score_one_idea()` builds prompt from template, calls OpenRouter light model, validates all 6 required keys, clamps scores to 1-10 range
- `run_quick_score()` collects all passed ideas, skips already-scored (idempotent), runs batch with asyncio.gather, writes results to frontmatter
- Shortlist produced by re-scanning 1_ideas/ for invest_score >= 6 OR build_score >= 6 after all writes complete

## Task Commits

1. **Task 1: LLM quick scoring module** - `fcaf1c0` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `pipeline/quick_score.py` — async LLM scoring stage: score_one_idea, run_quick_score, if __name__ == "__main__" block

## Decisions Made

- `score_one_idea` returns `None` on any validation failure (missing keys, non-dict result, Exception) rather than raising — allows `asyncio.gather` to cleanly collect all results without the `return_exceptions=True` catching mid-stream failures
- Shortlist built by re-scanning all `1_ideas/` files after the scoring round rather than accumulating in-memory — ensures idempotent re-runs where some ideas were pre-scored in a prior session are correctly included in the shortlist

## Deviations from Plan

None - plan executed exactly as written. File was already partially stubbed; verified it fully matched the spec and committed it.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Quick scoring stage complete, ready for run_pipeline.py orchestration (plan 01-04)
- Requires OPENROUTER_API_KEY and OPENROUTER_MODEL_LIGHT in .env for live runs
- Idempotent: safe to re-run after partial failures

---
*Phase: 01-mvp-dealpad-pipeline-end-to-end*
*Completed: 2026-04-10*

---
phase: 02-deep-research-pipeline-quality-upgrade
plan: 02
subsystem: pipeline
tags: [deep-analysis, stage-8, kill-signals, executive-summary, build-only, anchoring-fix]

# Dependency graph
requires:
  - phase: 02-deep-research-pipeline-quality-upgrade
    plan: 01
    provides: pipeline/deep_research_v2.py emitting 2_research/{slug}/deep_research.md (primary input for Stage 8)
  - phase: 01-mvp-dealpad-pipeline
    provides: pipeline/deep_analysis.py legacy structure, lib/llm.call_llm + load_prompt, lib/utils make_slug + load_idea, config/scoring_weights.yaml build_mode thresholds, idea frontmatter with build_thesis field
provides:
  - pipeline/deep_analysis.py — Stage 8 BUILD-ONLY: kill signals + 8-criterion build scoring + executive summary in frontmatter
  - prompts/deep_analysis.md — Russian prompt with i-Free context, {deep_research_content} + {build_thesis} inputs, build-only JSON output
  - config/scoring_weights.yaml — build_mode alignment comment; invest_mode preserved for future re-introduction
affects: [02-03-digest-update, 03-core-store-refactor, 04-production-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-scoring hard-filter pattern: kill signals extracted from LLM output, flag carried alongside scoring (not overloaded into verdict)"
    - "Verdict taxonomy enforcement via module-level constant + assert (VALID_BUILD_VERDICTS = {BUILD, PARTNER, MONITOR, SKIP})"
    - "Build-only architecture: invest scoring removed from prompt/code to eliminate anchoring bias; invest_mode weights preserved in config for future separate-prompt re-introduction"
    - ".replace() prompt substitution chain (continued — literal JSON braces incompatible with str.format)"
    - "Body markdown assembled via list + join to cleanly skip sections (scoring) when killed=True"

key-files:
  created: []
  modified:
    - pipeline/deep_analysis.py
    - prompts/deep_analysis.md
    - config/scoring_weights.yaml

key-decisions:
  - "Build-only architecture — invest scoring removed from Stage 8 prompt/code/frontmatter/body to fix anchoring bias and honour pipeline_tracks.invest=false default"
  - "Killed flag is informational: killed=true startups keep their computed build_verdict (never relabelled to PASS/WATCH); digest filters them via the killed flag, not the verdict label"
  - "VALID_BUILD_VERDICTS module constant + runtime assert enforces taxonomy at code level, not just in prompt"
  - "kill_reason derived from first triggered signal when LLM leaves it blank — defensive against underspecified LLM outputs"
  - "call_llm returning None (3-failure JSON parse) now raised as exception so run_deep_analysis counts it failed instead of writing a broken analysis file"
  - "Slug auto-discovery prefers deep_research.md but falls back to legacy research files so slugs from pre-Stage-7.5 still analyzable"
  - "invest_mode section in config/scoring_weights.yaml preserved unchanged — future invest-mode will use a separate prompt + LLM call, config location reused"

requirements-completed: [SC-05, SC-06, SC-07]

# Metrics
duration: ~8min
completed: 2026-04-14
---

# Phase 02 Plan 02: Deep Analysis Update Summary

**Stage 8 rewritten as BUILD-ONLY: reads the rich deep_research.md from Stage 7.5, applies 4 kill signals as a hard pre-scoring filter, and emits a Russian executive summary alongside build-mode scoring — anchoring-free, taxonomy-enforced in code.**

## Performance

- **Duration:** ~8 min
- **Tasks:** 2
- **Files modified:** 3 (deep_analysis.py, deep_analysis.md, scoring_weights.yaml)
- **Files created:** 0

## Accomplishments
- `prompts/deep_analysis.md` fully rewritten in Russian: i-Free context block (20+ years, portfolio Just AI / CoinKeeper / NaLunch, competencies AI/backend/mobile/fintech), `{deep_research_content}` as primary input, `{build_thesis}` as triage hypothesis to validate.
- 4 kill signals formalized in Step 1 of prompt: `market_occupied`, `high_capital`, `far_from_competencies`, `long_time_to_revenue`. If any triggered → `killed=true` but build scoring + executive summary still emitted.
- Build-only 8-criterion scoring (Step 2) with explicit taxonomy anchor — the prompt forbids PASS/WATCH and mandates `{BUILD, PARTNER, MONITOR, SKIP}`.
- Step 3 executive summary format with 7 Russian subsections (Суть / Рынок / Что строить / Целевой рынок / Time to market / Ключевые риски / Вердикт).
- `pipeline/deep_analysis.py.analyze_one` now reads `deep_research.md` (8000 char budget) as primary input, with legacy research files (`invest_research.md`, `build_research.md`, `web_research.md`, `website.md`) kept as fallback context.
- `build_thesis` extracted from idea frontmatter (`post.get("build_thesis") or "(none)"`) and threaded through the prompt.
- Kill signal extraction with `kill_reason` fallback: if LLM leaves `kill_reason` blank but `killed=true`, code derives it from the first triggered signal.
- Build verdict validated at runtime against `VALID_BUILD_VERDICTS = {"BUILD", "PARTNER", "MONITOR", "SKIP"}` via assert — taxonomy is a code-level invariant.
- Body markdown redesigned: header → killed notice (if killed, NOT labelled PASS) → Executive Summary → Build Score (skipped for killed) → Recommended Market → Time to Market → flags/risks/next_steps. Scoring section suppressed for killed startups (numbers are noise once the kill flag is set).
- Frontmatter carries all Plan 03 digest-consumer fields: `name`, `url`, `build_total`, `build_verdict`, `analyzed_at`, `killed`, `kill_reason`, `executive_summary`, `recommended_market`, `time_to_mvp`, `time_to_revenue`. `invest_total` and `invest_verdict` removed.
- Return dict from `analyze_one` updated: `{slug, build_total, build_verdict, killed, kill_reason}` (no invest fields).
- Slug auto-discovery in `run_deep_analysis` now prefers `deep_research.md` and still works with legacy files, so pre-Stage-7.5 slugs remain analyzable without a forced backfill.
- `call_llm` returning `None` (its 3-attempt JSON-parse fallback path) now surfaces as `RuntimeError` so `asyncio.gather(..., return_exceptions=True)` counts it as failed rather than writing a corrupt analysis file.
- `config/scoring_weights.yaml` build_mode header comment states alignment with `docs/Deep Analysis Upgrade Plan.md` and the canonical taxonomy; invest_mode section documented as preserved-for-future (not read by Stage 8).

## Task Commits

1. **Task 1: Rewrite `prompts/deep_analysis.md` with kill signals + build-only architecture** — `6d29222` (feat)
2. **Task 2: Rewrite `pipeline/deep_analysis.py` as BUILD-ONLY with kill signals + update `config/scoring_weights.yaml`** — `cca5cc4` (feat)

## Files Created/Modified

- `prompts/deep_analysis.md` (modified) — full rewrite: Russian role/context, kill signals, build-only scoring, executive summary format, JSON output schema without invest_* / cis_adaptation.
- `pipeline/deep_analysis.py` (modified) — analyze_one reads deep_research.md + build_thesis; extracts kill signals and executive_summary; enforces build-only verdict taxonomy via module constant + assert; body markdown redesigned; run_deep_analysis slug discovery updated.
- `config/scoring_weights.yaml` (modified) — build_mode alignment comment; invest_mode preservation comment; weights unchanged (already aligned with spec).

## Decisions Made

- **Build-only in Stage 8:** invest scoring removed from the same prompt context to eliminate anchoring bias. Re-introduction will be a separate prompt + LLM call in a future phase. Rationale reinforced by `pipeline_tracks.invest: false` default and the 02-CONTEXT.md explicit build-only decision.
- **Killed flag is informational, not a verdict label:** killed startups keep a real computed verdict from the four-value taxonomy. Digest routing in Plan 03 will filter by `killed=True`. This avoids overloading `build_verdict` with PASS (an invest-taxonomy term that was retired).
- **Taxonomy enforcement in code, not only in prompt:** `VALID_BUILD_VERDICTS = {BUILD, PARTNER, MONITOR, SKIP}` + assert in `analyze_one`. An LLM returning an off-taxonomy verdict is a hard failure — the assertion fires, the task raises, and `run_deep_analysis` logs it instead of silently corrupting the analysis file.
- **Derive kill_reason fallback:** if `killed=True` but `kill_reason==""`, walk `kill_signals` and take the first triggered signal's reason. LLM prompts can't always be trusted to fill two coupled fields consistently — defensive extraction is cheap.
- **`call_llm` None-return promotion:** `run_deep_analysis` treats `None` as failure by raising `RuntimeError` inside `analyze_one`. Before this, `None.get(...)` would have raised `AttributeError` mid-assembly; now the error mode is explicit and the fail counter in the return dict stays accurate.
- **Preserve invest_mode in scoring_weights.yaml:** future invest-mode re-introduction will reuse this exact YAML path — deleting the section now would force a later migration. Comment documents why it's dormant.
- **Body scoring section omitted when killed:** scoring numbers on a killed startup are noise and would clutter the analysis file. The frontmatter still carries `build_total` for completeness / future filtering.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Hardened `call_llm` None-return handling in analyze_one**
- **Found during:** Task 2
- **Issue:** `lib.llm.call_llm` returns `None` after 3 consecutive JSON-parse failures (per Phase 01 bugfix). The original `deep_analysis.py` only guarded against `Exception` return; a `None` return would crash later at `result.get(...)` inside the kill-signal block, raising `AttributeError` mid-construction with no file cleanup.
- **Fix:** Added explicit `if result is None: raise RuntimeError(...)` right after the existing `isinstance(result, Exception)` check. Now `run_deep_analysis` captures it via `asyncio.gather(return_exceptions=True)` and counts it as a normal failure.
- **Files modified:** `pipeline/deep_analysis.py`
- **Commit:** `cca5cc4`

**2. [Rule 3 - Blocking] Restored Wave 1 artifacts deleted from worktree**
- **Found during:** Initial worktree inspection
- **Issue:** After `git reset --soft ce30248...` the working tree still had the pre-reset state — which had `lib/parallel_client.py`, `pipeline/deep_research_v2.py`, `prompts/deep_research_brief.md`, and `.planning/phases/02-deep-research-pipeline-quality-upgrade/02-01-SUMMARY.md` marked deleted. Plan preamble explicitly said these Wave 1 artifacts are "already on main and available"; their absence would have blocked import resolution and mis-framed the context for this plan.
- **Fix:** `git checkout HEAD -- <4 paths>` to restore them from the soft-reset HEAD (where they exist, having been added by the preceding 02-01 commits).
- **Files modified:** none — all four paths are Wave 1 outputs, not in this plan's scope.
- **Commit:** not committed by this plan (restoration only, files already match HEAD).

### Verdict wording in killed body

The plan text in Task 2 body markdown spec (line 296) reads `Digest will show under "PASS via kill signal" section._`, which contradicts the plan's own verify block (`assert 'PASS' not in src`) and the 02-CONTEXT.md verdict-taxonomy guidance. Resolved by keeping the killed notice informational without the literal string "PASS" — the body says "digest routes killed startups into a dedicated filtered-out section". Digest naming is a Plan 02-03 concern; Stage 8 does not hard-code digest section labels.

## Issues Encountered

- **Live smoke test not executed.** The plan's smoke test requires `2_research/deeptrace/deep_research.md` to exist (produced by Stage 7.5, which requires a live `PARALLEL_API_KEY` — per 02-01-SUMMARY.md that key is still an operator setup prerequisite). Running the smoke test now would burn OpenRouter credits on a slug with no real research input. Instead, the module was verified via static analysis (syntax check, import check, taxonomy-enforcement round-trip through `determine_verdict` for all 4 tiers, YAML load check of `config/scoring_weights.yaml`). All `<verification>` block automated assertions from the plan pass.
- **Pre-existing uncommitted changes left untouched** in `.env.example`, `.planning/ROADMAP.md`, `.planning/STATE.md`, `docs/demo-dashboard.html`, `lib/exa_client.py`, `lib/llm.py`. Per `pre_existing_uncommitted` directive, none of these were staged, modified, or committed.

## User Setup Required

**To run the full smoke test end-to-end:**
1. Set `PARALLEL_API_KEY=<key>` in `.env` (see `.env.example` for format; source = Parallel AI dashboard).
2. Ensure `OPENROUTER_API_KEY` and `OPENROUTER_MODEL_HEAVY` are set.
3. Run:
   ```bash
   cd /Users/eli/Documents/PythonProjects/StartupScanner && \
     rm -f 3_analysis/deeptrace_analysis.md && \
     python -c "
   import asyncio
   from pipeline.deep_research_v2 import run_deep_research_v2
   from pipeline.deep_analysis import run_deep_analysis
   asyncio.run(run_deep_research_v2(['deeptrace']))
   r = asyncio.run(run_deep_analysis(slugs=['deeptrace']))
   print(r)
   " && \
     python -c "
   import frontmatter
   p = frontmatter.load('3_analysis/deeptrace_analysis.md')
   assert p.get('build_verdict') in {'BUILD', 'PARTNER', 'MONITOR', 'SKIP'}
   assert isinstance(p.get('killed'), bool)
   assert p.get('executive_summary')
   assert 'invest_total' not in p.metadata and 'invest_verdict' not in p.metadata
   print('smoke OK: build_verdict=%s killed=%s' % (p['build_verdict'], p['killed']))
   "
   ```

## Next Phase Readiness

- Stage 8 is feature-complete and unblocked for Plan 02-03 (digest) — all frontmatter fields listed in the plan's `<interfaces>` contract are emitted: `killed`, `kill_reason`, `executive_summary`, `build_verdict ∈ {BUILD, PARTNER, MONITOR, SKIP}`, `build_total`, `recommended_market`, `time_to_mvp`, `time_to_revenue`.
- Plan 02-03 (digest) can rely on `killed` as the routing flag — it must NOT filter by verdict label, because killed startups keep their computed verdict.
- Plan 02-03 must be defensive: old pre-Phase-2 analysis files in `3_analysis/` still carry `invest_total`/`invest_verdict` frontmatter. The digest generator should tolerate missing keys, not crash.
- Any future invest-mode re-introduction (post-Phase-2) will use a separate prompt + LLM call; the invest_mode section in `config/scoring_weights.yaml` is preserved for that path.
- Wiring of Stage 7.5 into `run_pipeline.py` (between build gate and Stage 8) remains open — tracked in Plan 02-01 summary's next-phase readiness and applies here too.

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`. All four STRIDE threats are handled as specified:
- T-02-05 (Tampering of deep_research.md content in prompt): accepted — text-only, goes through LLM, no code execution.
- T-02-06 (Info disclosure in executive_summary): accepted — analysis files are internal.
- T-02-07 (EoP via killed=true override): mitigated via taxonomy-validated verdict + informational kill flag. Code does NOT overload `build_verdict` when killed, but the killed flag itself is set by the LLM — the mitigation pattern now differs from the plan text (plan suggested hard-coding `build_verdict="PASS"`; we rejected that in favour of informational flag + code-level taxonomy assert). Net protection equivalent: LLM cannot smuggle a high score past a killed flag because the digest (Plan 02-03) filters by `killed=True`, not by verdict label.
- T-02-08 (DoS via oversized deep_research.md): mitigated — content truncated to 8000 chars via `[:8000]` slice before prompt injection.

## Self-Check: PASSED

- `prompts/deep_analysis.md` — FOUND; contains `{deep_research_content}`, `{build_thesis}`, `{name}`, kill signals, build-only scoring, executive summary format; no invest_*; no cis_adaptation.
- `pipeline/deep_analysis.py` — FOUND; `analyze_one` contains `deep_research`, `killed`, `executive_summary`, `kill_reason`, `build_thesis`; no `PASS`; no `invest_total`; no `invest_verdict`; no `invest_scoring`; no `cis_adaptation`; `VALID_BUILD_VERDICTS` constant present; `recommended_market`, `time_to_mvp`, `time_to_revenue` extracted. `run_deep_analysis` auto-discovery includes `deep_research.md`.
- `config/scoring_weights.yaml` — FOUND; build_mode weights sum to 1.0; invest_mode preserved untouched (weights unchanged).
- Commit `6d29222` — FOUND.
- Commit `cca5cc4` — FOUND.
- Plan `<verification>` block (4 checks):
  - `analyze_one` reads `deep_research` — PASSED.
  - `analyze_one` handles `killed` — PASSED.
  - Prompt contains `kill` — PASSED.
  - Weights YAML has `build_mode` — PASSED.
- Taxonomy round-trip on `determine_verdict`: 9.0→BUILD, 7.0→PARTNER, 5.0→MONITOR, 2.0→SKIP — PASSED.

---
*Phase: 02-deep-research-pipeline-quality-upgrade*
*Completed: 2026-04-14*

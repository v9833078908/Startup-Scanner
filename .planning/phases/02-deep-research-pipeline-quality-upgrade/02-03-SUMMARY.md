---
phase: 02-deep-research-pipeline-quality-upgrade
plan: 03
subsystem: pipeline
tags: [digest, stage-9, stage-7.5-wiring, deterministic-first, invest-guard, byte-for-byte-exec-summary]

# Dependency graph
requires:
  - phase: 02-deep-research-pipeline-quality-upgrade
    plan: 01
    provides: pipeline/deep_research_v2.py run_deep_research_v2 entry point consumed by Stage 7.5 wiring in run_pipeline.py
  - phase: 02-deep-research-pipeline-quality-upgrade
    plan: 02
    provides: 3_analysis/{slug}_analysis.md frontmatter fields (build_verdict in {BUILD,PARTNER,MONITOR,SKIP}, killed, kill_reason, executive_summary, recommended_market, time_to_mvp, time_to_revenue) consumed by digest_generator.collect_analyses
provides:
  - pipeline/digest_generator.py — Stage 9 DETERMINISTIC-FIRST: Python composes per-startup sections with byte-for-byte executive_summary insertion; narrow LLM synthesis only for Ключевые находки + Тренды
  - prompts/digest.md — narrow synthesis prompt emitting only {key_findings, trends} JSON; uses {summary_data} variable
  - run_pipeline.py — Stage 7.5 wired between build gate and deep analysis; honest invest guard (SystemExit when invest enabled); stages renumbered to N/10
  - README.md — pipeline diagram + temporary invest limitation callout
affects: [02-04-context-enrichment, 03-multi-source-delivery, 04-research-quality, 05-production-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deterministic-first digest: Python templates for per-startup blocks, narrow LLM call restricted to synthesis sections (key_findings + trends) — guarantees Stage 8 wording reaches digest byte-for-byte"
    - "Honest failure pattern: explicit SystemExit on incompatible track config (invest_enabled + BUILD-ONLY deep_analysis) — louder than silent wrong scoring"
    - "Graceful backward compat via post.get() with defaults — legacy invest_total/invest_verdict frontmatter no longer raises KeyError"
    - "Narrow LLM synthesis with sentinel fallbacks — generate_synthesis_with_llm never raises; deterministic sections render regardless of LLM availability"
    - "Stage renumbering with decimal suffix (7.5/10) — matches Plan 01's canonical Stage 7.5 naming convention"

key-files:
  created:
    - .planning/phases/02-deep-research-pipeline-quality-upgrade/02-03-SUMMARY.md
  modified:
    - pipeline/digest_generator.py
    - prompts/digest.md
    - run_pipeline.py
    - README.md

key-decisions:
  - "Deterministic-first digest — per 02-CONTEXT.md Stage 9 decisions; LLM-first re-synthesizes executive summaries (compresses/paraphrases Stage 8 output) while deterministic Python paste guarantees byte-for-byte insertion"
  - "Removed build_digest_manually and generate_digest_with_llm entirely (not kept as fallback) — replaced by build_digest_deterministic + narrow generate_synthesis_with_llm; legacy functions would confuse future maintainers"
  - "Researched counter fix — now checks web_research.md OR build_research.md OR deep_research.md (was legacy-only, making digest show 'Researched: 0' after Phase 2 file reshuffling)"
  - "Narrow LLM contract: LLM sees counts + per-startup metadata (no executive_summaries); Python handles all per-startup rendering — LLM cannot leak numeric scores or paraphrase Stage 8 content"
  - "Honest invest guard location — placed right before deep_analysis call, only fires when invest_ready is non-empty (empty invest_ready = no harm, no block)"
  - "README.md pipeline diagram updated to include [7.5] Deep Research; invest-limitation callout added directly under diagram for visibility (not buried in roadmap section)"

requirements-completed: [SC-08, SC-09, SC-11]

# Metrics
duration: ~10min
completed: 2026-04-14
---

# Phase 02 Plan 03: Digest Upgrade + Pipeline Wiring Summary

**Stage 9 rewritten as DETERMINISTIC-FIRST: Python templates paste Stage 8 executive_summary BYTE-FOR-BYTE into BUILD/MONITOR sections, kill reasons into a PASS-via-kill-signals table; narrow LLM call handles only Ключевые находки + Тренды synthesis. Stage 7.5 wired into run_pipeline.py between build gate and deep analysis. Honest invest guard raises SystemExit when pipeline_tracks.invest=true (Phase 2 is BUILD-ONLY).**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2
- **Files modified:** 4 (pipeline/digest_generator.py, prompts/digest.md, run_pipeline.py, README.md)
- **Files created:** 0 (SUMMARY is metadata, not source)

## Accomplishments

- `prompts/digest.md` rewritten as narrow synthesis prompt — outputs ONLY `{key_findings, trends}` JSON; uses `{summary_data}` variable (not `{analysis_data}`); explicit rules: no per-startup descriptions, no numeric scores, no fabrications, Russian language.
- `pipeline/digest_generator.py` rewritten around a deterministic core:
  - NEW `build_digest_deterministic(stats, analyses, llm_synthesis)` — 6-section digest: Pipeline Summary → Ключевые находки → BUILD рекомендации → MONITOR → PASS via kill signals → Тренды недели.
  - BUILD/MONITOR blocks paste `executive_summary` BYTE-FOR-BYTE (no LLM rewriting) — Stage 8 wording survives intact into the management-facing artifact.
  - PASS-via-kill-signals section renders a deterministic table `| name | category | kill_reason |` filtered by `killed=True`; killed startups never leak into BUILD/MONITOR sections despite retaining their computed `build_verdict`.
  - NEW `generate_synthesis_with_llm(stats, analyses)` — narrow LLM call; sends only counts + per-startup metadata (no `executive_summary`); never raises, returns `"_(LLM synthesis unavailable — …)_"` sentinels on error; tiny-dataset fast path when `analyses` is empty.
  - `collect_analyses()` extended with all Plan 02-02 digest-consumer fields: `killed`, `kill_reason`, `executive_summary`, `recommended_market`, `time_to_mvp`, `time_to_revenue`; legacy `invest_total`/`invest_verdict` preserved via `post.get()` with `None` defaults (backward compat; not rendered in digest).
  - `collect_pipeline_stats()` — `researched` counter now checks web/build/deep_research.md (was legacy-only, making "Researched: 0" post-Phase-2); new `deep_researched` counter surfaces Stage 7.5 visibility; new `killed` counter powers Section 5.
  - REMOVED: `build_digest_manually()`, `generate_digest_with_llm()`, `build_digest_data()`, `_extract_section()`, `_load_pipeline_tracks()` — replaced by deterministic core + narrow synthesis; legacy fallbacks deleted rather than kept dormant.
  - `run_digest()` linearized: collect → stats → synthesis → deterministic build → write file. No more LLM-vs-template branching. Digest filename logic unchanged (`_run2`, `_run3`, … suffix on collision — honours MEMORY "no overwrite digests" feedback).
- `run_pipeline.py` — Stage 7.5 wired:
  - `from pipeline.deep_research_v2 import run_deep_research_v2` added.
  - New `[7.5/10] Deep Research via Parallel AI` block inserted between `[7/10] Build gate` and `[8/10] Deep analysis`; only runs when `build_enabled and build_ready` is non-empty.
  - Final summary logging includes `Deep research (Parallel AI): N`.
  - All other stages renumbered `N/9 → N/10`; argparse description `9-stage dual-track funnel` → `10-stage build-track funnel with deep research`.
- `run_pipeline.py` — honest invest guard: immediately before `run_deep_analysis`, explicit `SystemExit` when `invest_enabled and invest_ready` is non-empty; logs a clear error explaining the Phase 2 BUILD-ONLY limitation and the two ways to unblock (disable invest track or wait for future phase).
- `README.md` — pipeline diagram updated to include `[7.5] Deep Research via Parallel AI`; visible callout directly under the diagram documents the Phase 2 invest-track temporary limitation (ROADMAP.md already carried this text from prior planning).

## Task Commits

1. **Task 1: Rewrite prompts/digest.md + pipeline/digest_generator.py — management-ready digest** — `dfc95ce` (feat)
2. **Task 2: Wire Stage 7.5 into run_pipeline.py + honest invest guard + README update** — `67bfe22` (feat)

## Files Created/Modified

- `pipeline/digest_generator.py` (modified) — deterministic-first Stage 9: `build_digest_deterministic`, `generate_synthesis_with_llm`, extended `collect_analyses`, fixed `collect_pipeline_stats`; legacy `build_digest_manually`/`generate_digest_with_llm` removed.
- `prompts/digest.md` (modified) — narrow synthesis prompt: `{summary_data}` input, JSON output `{key_findings, trends}`, Russian with tech terms in English, no per-startup descriptions, no numeric scores.
- `run_pipeline.py` (modified) — `run_deep_research_v2` import; `[7.5/10]` block between build gate and deep analysis; honest invest guard (`SystemExit` when invest enabled with ready slugs); stage log renumbering `N/9 → N/10`; argparse description updated; `Deep research (Parallel AI)` line in final summary.
- `README.md` (modified) — pipeline diagram with `[7.5]` Deep Research; Phase 2 invest-limitation callout under the diagram.

## Decisions Made

- **Deterministic-first digest over LLM-first.** Per 02-CONTEXT.md Stage 9 decisions: LLM-first violates the "executive summaries go directly, not re-synthesized" promise — LLMs paraphrase/compress even with strict prompts. The new architecture composes per-startup blocks in Python and uses the LLM only for synthesis sections that are meant to be generated (Key Findings, Trends). Narrow scope protects Stage 8 wording AND forbids numeric score leakage (the LLM doesn't see scores).
- **Removed legacy fallbacks rather than keep them dormant.** `build_digest_manually` and `generate_digest_with_llm` would confuse future maintainers ("which path is canonical?"). The deterministic builder is the only path; LLM-synthesis fallback is inline via sentinel strings when `generate_synthesis_with_llm` fails.
- **Researched counter bug auto-fixed (Rule 1).** The plan mandated the fix; surfaced during code review: the current counter only looked for `web_research.md`, but Phase 2 research dirs contain `deep_research.md` + `build_research.md`. Without the fix, the digest would display "Researched: 0" after a successful Phase 2 run. Also added `deep_researched` counter for Stage 7.5 visibility.
- **Honest invest guard location: just before deep_analysis call.** Alternative was at pipeline start (fail earlier). Chose just-before-deep-analysis because: (a) parsing + triage are still useful signal even if invest is misconfigured, (b) no invest_ready slugs means no harm — the guard only fires when there's a real risk of silent build-scoring on invest candidates.
- **README diagram callout, not just ROADMAP prose.** ROADMAP.md already carried the Phase 2 invest limitation text from earlier planning. The new callout directly under the README pipeline diagram makes it visible to anyone reading the high-level doc — not buried in the roadmap section.
- **Narrow LLM contract: counts + metadata only, NEVER executive_summaries.** The LLM prompt's `{summary_data}` payload is explicitly constructed in `_build_summary_payload` — it sends `name`, `category`, `build_verdict`, `killed`, `kill_reason`, `recommended_market`. The `executive_summary` field is deliberately excluded. This guarantees the LLM cannot paraphrase Stage 8 content back into the digest.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored prior-wave artifacts missing from worktree**
- **Found during:** initial worktree inspection
- **Issue:** `git reset --soft 9f9425b` returned the index to the base, but the worktree had prior-wave files (`lib/parallel_client.py`, `pipeline/deep_research_v2.py`, `prompts/deep_research_brief.md`, `02-01-SUMMARY.md`, `02-02-SUMMARY.md`) marked deleted (existed in HEAD, absent from disk) plus spurious modifications to `pipeline/deep_analysis.py`/`prompts/deep_analysis.md`/`config/scoring_weights.yaml`/`.env.example` that reverted the Plan 02-01/02-02 work. Per plan preamble, these are "prior waves already on main" — absence would have broken imports for Stage 7.5 wiring.
- **Fix:** `git checkout HEAD -- <paths>` for each prior-wave file/SUMMARY to realign worktree with HEAD. No commit from this plan touched these paths.
- **Commit:** N/A — restoration only, files match HEAD.

### Additional notes (not auto-fixes)

- Pre-existing uncommitted changes in `.planning/STATE.md`, `docs/demo-dashboard.html`, `lib/exa_client.py`, `lib/llm.py` left UNTOUCHED per `<pre_existing_uncommitted>` directive. None of these are in this plan's `files_modified` list.
- Two auxiliary functions (`build_digest_data`, `_extract_section`, `_load_pipeline_tracks`) were deleted alongside the two named legacy functions because they were dead code once `build_digest_manually` and `generate_digest_with_llm` were removed. Not a deviation — scope of "REMOVE" in plan text implicitly covered their call graph.

## Issues Encountered

- **Live smoke test against real analysis files not executed.** The plan's smoke test calls `run_digest()` end-to-end and asserts that `deeptrace`'s executive_summary appears byte-for-byte in the digest. Running it now would require: (1) `PARALLEL_API_KEY` and `OPENROUTER_API_KEY` set in `.env` (operator setup — per 02-01-SUMMARY.md the Parallel key is still a pending operator step), (2) a successful Stage 7.5 run on `deeptrace`, (3) a successful Stage 8 run producing `3_analysis/deeptrace_analysis.md`. Instead, verified via an **offline smoke test**: constructed three synthetic analyses (BUILD, MONITOR, killed), called `build_digest_deterministic` directly, asserted: byte-for-byte executive_summary insertion, killed startup excluded from BUILD section and present in PASS-via-kill-signals, no numeric score leakage (regex `\d\.\d+/10`, `score: \d`, `build_total`, `invest_total`). All checks passed.
- **Honest-invest-guard smoke test not run.** Requires toggling `config/triage.yaml` to `invest: true` and running `python run_pipeline.py --html ...` with a real HTML export; that flow hits the network (OpenRouter) for triage. Verified via static analysis: `inspect.getsource(main)` contains `'invest_enabled' in src and 'SystemExit' in src and 'Phase 2 build-only deep_analysis cannot run' in src` — the guard is present at the correct location (right before `run_deep_analysis`) and carries the explicit error message.

## User Setup Required

**No new user setup beyond Plan 02-01's `PARALLEL_API_KEY` requirement.** The digest generator uses the existing `OPENROUTER_MODEL_LIGHT` model (already configured) for the narrow synthesis call; deterministic sections render regardless of LLM availability.

## Next Phase Readiness

- Plan 02-04 (context enrichment for Parallel AI + Stage 8) unblocked — all Plan 02-03 artifacts in place; neither Stage 7.5 wiring nor the digest generator change the interfaces 02-04 will touch.
- Full Phase 2 pipeline is feature-complete pending live validation: `python run_pipeline.py --html …` on a real export will exercise Stages 1→10 end-to-end once `PARALLEL_API_KEY` is configured.
- Future invest-mode re-introduction (post-Phase-2) must remove the honest invest guard in `run_pipeline.py` AND add a separate invest_analysis entry point; `config/scoring_weights.yaml` invest_mode section is already preserved for that path.

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`. All four STRIDE threats (T-02-09 info disclosure, T-02-10 tampering of executive_summary passthrough, T-02-11 DoS of deep_research_v2, T-02-12 repudiation) are handled as specified:

- **T-02-09 (info disclosure):** accepted — digest consumes public aggregated startup data for internal use. No secrets rendered.
- **T-02-10 (tampering passthrough):** mitigated operationally — digest does not re-synthesize executive summaries; LLM cannot paraphrase/inject content into per-startup blocks because it never receives them. Stage 8's content reaches the digest byte-for-byte.
- **T-02-11 (DoS deep_research_v2):** mitigated — Stage 7.5 skipped gracefully when `build_ready` empty or `build_enabled=False`; pipeline continues to Stage 8 even if `run_deep_research_v2` reports failures (it never raises at the orchestrator level — per Plan 02-01, failed calls write stubs).
- **T-02-12 (repudiation from score-less digest):** accepted — scoring preserved in `3_analysis/` files (build_total, build_verdict remain in frontmatter); digest is a presentation layer only.

## Self-Check: PASSED

- `prompts/digest.md` — FOUND; contains `{summary_data}`, `key_findings`, `trends`; NO `{analysis_data}`; NO numeric-score instructions.
- `pipeline/digest_generator.py` — FOUND; `build_digest_deterministic`, `generate_synthesis_with_llm`, `collect_analyses`, `collect_pipeline_stats` present; legacy `build_digest_manually`/`generate_digest_with_llm` removed; `researched` counter checks `deep_research.md`/`build_research.md`/`web_research.md`; `deep_researched` + `killed` counters present.
- `run_pipeline.py` — FOUND; imports `run_deep_research_v2`; Stage 7.5 block with `[7.5/10]` log line; honest invest guard (`SystemExit`, `invest_enabled`, explicit Phase 2 error message); argparse says `10-stage build-track funnel`; `Deep research (Parallel AI)` in final summary.
- `README.md` — FOUND; `[7.5] Deep Research via Parallel AI` in pipeline diagram; Phase 2 invest-limitation callout present.
- Commit `dfc95ce` — FOUND.
- Commit `67bfe22` — FOUND.
- Plan `<verification>` block (4 checks):
  - Stage 7.5 wired + honest invest guard — PASSED.
  - digest prompt is narrow synthesis (`{summary_data}`, `key_findings`) — PASSED.
  - New function names exist (`build_digest_deterministic`, `generate_synthesis_with_llm`) — PASSED.
  - Offline smoke test (deterministic builder, byte-for-byte insertion, no score leakage, killed filter) — PASSED.
- Full import chain resolves: `run_pipeline` → `deep_research_v2` → `parallel_client` → `digest_generator` → `deep_analysis` — PASSED.

---
*Phase: 02-deep-research-pipeline-quality-upgrade*
*Completed: 2026-04-14*

---
phase: 02-deep-research-pipeline-quality-upgrade
verified: 2026-04-14T00:00:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "End-to-end live pipeline run with real PARALLEL_API_KEY + OPENROUTER_API_KEY"
    expected: "python run_pipeline.py --html <dealpad_export.html> completes all 10 stages; 2_research/{slug}/deep_research.md files contain substantive (>500 chars) Russian content with ## Источники sections (not '(Deep research failed:' stubs); 3_analysis/{slug}_analysis.md files have non-empty executive_summary, build_verdict ∈ {BUILD,PARTNER,MONITOR,SKIP}; digests/{YYYY}-W{WW}_weekly.md is management-ready with byte-for-byte executive_summary insertion."
    why_human: "All 4 summaries explicitly report no live smoke tests executed — operator PARALLEL_API_KEY not set at execution time. All code paths and prompt assembly verified statically; live API call quality (content depth, citation accuracy, language compliance) requires human review of actual deep_research.md and digest output."
  - test: "Honest invest guard live trigger"
    expected: "Set pipeline_tracks.invest=true in config/triage.yaml, run pipeline with a dealpad export that produces at least one invest-routed startup passing invest gate. Pipeline must raise SystemExit with 'Phase 2 build-only deep_analysis cannot run with invest track enabled' message. Restore config after test."
    why_human: "Static source inspection confirms guard presence at correct location; live trigger requires real HTML export + network calls for triage + invest gate."
  - test: "Digest content quality (Dina's requirement)"
    expected: "Generated digest is readable by non-technical management; executive summaries cover Суть/Рынок/Что строить/Целевой рынок/Time to market/Ключевые риски/Вердикт per startup; no numeric scoring leaked; PASS via kill signals section lists killed startups with meaningful kill_reason."
    why_human: "The Phase 2 goal is 'informative management-ready output' — requires human evaluation of writing quality, coherence, and usefulness for strategic decisions. Automated checks only verify mechanics."
  - test: "Anti-anchoring effect on Parallel AI output"
    expected: "Compare Parallel AI deep_research.md content against preliminary Stage 5 build_research.md: Parallel AI should VALIDATE/REFUTE/EXTEND the preliminary findings with independent citations, not merely paraphrase. Spot-check on 2-3 slugs."
    why_human: "Anti-anchoring framing is a qualitative prompt-engineering outcome — requires reading multiple deep_research.md outputs to evaluate whether the LLM is challenging preliminaries rather than confirming them."
---

# Phase 2: Deep Research + Pipeline Quality Upgrade Verification Report

**Phase Goal:** Add Deep Research stage (7.5) via Parallel AI Task API, upgrade Deep Analysis (Stage 8) with kill signals + executive summaries, upgrade Digest (Stage 9) for informative management-ready output.

**Verdict Taxonomy (canonical):** `build_verdict ∈ {BUILD, PARTNER, MONITOR, SKIP}`; separate `killed: bool` + `kill_reason: str`.

**Verified:** 2026-04-14
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Merged from ROADMAP Success Criteria + PLAN must_haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `lib/parallel_client.py` — async client for Parallel AI Task API (create / get / convenience) | ✓ VERIFIED | Exports `create_task_run`, `get_task_result`, `run_deep_research_task`, `extract_citations`. httpx-based, lazy API-key loading, two-level citations iteration, never-raises convenience wrapper. Imports OK. |
| 2 | `pipeline/deep_research_v2.py` — Stage 7.5 deep research module, idempotent, route-filtered, concurrency-bounded | ✓ VERIFIED | `run_deep_research_v2(slugs)` exists; route filter `('build','both')`; `Semaphore(3)`; idempotency check on `deep_research.md`; writes `2_research/{slug}/deep_research.md` with citations section; legacy `pipeline/deep_research.py` untouched (confirmed via ls). |
| 3 | `prompts/deep_research_brief.md` — 6-section Russian research brief + anti-anchoring preliminary findings section | ✓ VERIFIED | Contains all 10 template variables: `{name}`, `{url}`, `{description}`, `{round_raw}`, `{category}`, `{build_thesis}`, `{raw_evidence}`, `{preliminary_findings}`, `{gate_signals}`, `{website_summary}`. Contains 6 "Что исследовать" sections (Суть/TAM/Конкуренты/Валидация/Build/География). Contains VALIDATE/REFUTE/EXTEND/CHALLENGE anti-anchoring framing. Raw evidence labelled "PRIMARY independent data"; Stage 5 LLM synthesis labelled "SECONDARY hint — cheap-LLM interpretation, may be wrong". |
| 4 | Output: `2_research/{slug}/deep_research.md` with citations | ✓ VERIFIED | `research_one_deep` writes to `research_dir / "deep_research.md"` with header + content + `_format_citations` output (`## Источники` section). Stub file on API failure also written here (idempotency pattern). |
| 5 | Updated `pipeline/deep_analysis.py` — BUILD-ONLY with kill signals + executive summary | ✓ VERIFIED | `analyze_one` reads `deep_research.md` (8000-char budget), `build_thesis`, `gate_signals`. Extracts `kill_signals`, `killed`, `kill_reason` (with fallback derivation). `VALID_BUILD_VERDICTS = {BUILD, PARTNER, MONITOR, SKIP}` + runtime assert. Writes frontmatter with `killed`, `kill_reason`, `executive_summary`, `recommended_market`, `time_to_mvp`, `time_to_revenue`. Zero `invest_total`/`invest_verdict`/`invest_scoring` references (grep-verified). |
| 6 | Updated `prompts/deep_analysis.md` — kill signals + i-Free context + executive summary format + build-only | ✓ VERIFIED | Role "аналитик стартап-студии i-Free"; i-Free context (Just AI, CoinKeeper, NaLunch, 20+ years); Шаг 1 with 4 kill signals (market_occupied, high_capital, far_from_competencies, long_time_to_revenue); Шаг 2 build-only 8-criterion table; Шаг 3 executive_summary 7-field format (Суть/Рынок/Что строить/Целевой рынок/Time to market/Ключевые риски/Вердикт); JSON output with `build_verdict ∈ {BUILD, PARTNER, MONITOR, SKIP}` explicit prohibition of PASS/WATCH; `{gate_signals}` threaded in with anti-anchoring note "доверяй deep research, отметь расхождение". |
| 7 | Updated `config/scoring_weights.yaml` — build_mode aligned, invest_mode preserved | ✓ VERIFIED | `build_mode` weights sum to 1.00 (30+25+15+10+10+5+3+2), thresholds BUILD≥8/PARTNER≥6/MONITOR≥4/SKIP≥0. Header comment documents build-only canon taxonomy. `invest_mode` section preserved unchanged with explanatory comment (not read by Stage 8 anymore). |
| 8 | Updated `pipeline/digest_generator.py` — DETERMINISTIC-FIRST with byte-for-byte executive_summary insertion | ✓ VERIFIED | `build_digest_deterministic` composes 6 sections in Python; `_render_startup_block` pastes `executive_summary` byte-for-byte; `generate_synthesis_with_llm` narrow scope (only `{key_findings, trends}`, LLM never sees executive_summary); `_build_summary_payload` explicitly excludes `executive_summary`; never-raises sentinel fallback. Legacy `build_digest_manually`/`generate_digest_with_llm` removed. Killed startups filtered into "PASS via kill signals" table by `killed=True`, not by verdict label. Offline smoke test confirmed byte-for-byte insertion, no numeric score leakage (`\d\.\d+/10`, `build_total`, `/10` all absent from rendered output). `researched` counter checks web/build/deep_research.md (Phase 2 fix); `deep_researched` + `killed` counters added. |
| 9 | Updated `prompts/digest.md` — narrow synthesis emitting only `{key_findings, trends}` | ✓ VERIFIED | Uses `{summary_data}` variable (not `{analysis_data}`). Explicit prohibitions: "НЕ добавляй описания конкретных стартапов", "НЕ добавляй численные скоринги", "НЕ придумывай факты". Output contract: JSON with exactly two keys `key_findings`, `trends`. |
| 10 | Updated `run_pipeline.py` — Stage 7.5 wired + honest invest guard | ✓ VERIFIED | Imports `run_deep_research_v2`. `[7.5/10]` block placed between `[7/10] Build gate` and `[8/10] Deep analysis`; only runs when `build_enabled and build_ready`. Honest invest guard raises `SystemExit("Phase 2 build-only deep_analysis cannot run with invest track enabled…")` right before `run_deep_analysis` call when `invest_enabled and invest_ready`. All stages renumbered to `N/10`. argparse description: "10-stage build-track funnel with deep research". Final summary logs `Deep research (Parallel AI): N`. README pipeline diagram shows `[7.5] Deep Research via Parallel AI` + temporary-limitation callout. ROADMAP.md carries Phase 2 BUILD-ONLY note line 27. |
| 11 | `PARALLEL_API_KEY` env var documented | ✓ VERIFIED | `.env.example` lines 11-16: "Parallel AI Task API — deep research for gate-passed startups (Stage 7.5)", "core" processor ($0.025/run) documented, stub-on-failure retry guidance included. |

**Additional truth from Plan 02-04 (shared helper home):**

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 12 | `lib/research_utils.py` — shared helpers, identity-equal across consumers | ✓ VERIFIED | Module exists with `_format_gate_signals` and `_format_raw_evidence`. Both graceful (return explicit placeholder strings for missing/malformed/unparseable inputs, never raise). Module docstring documents the architectural rule (pipeline modules never import from each other for shared helpers). Runtime identity check `pipeline.deep_research_v2._format_gate_signals is pipeline.deep_analysis._format_gate_signals` → **True** (Python module caching). Parse output verified on real `2_research/21st/gate_build.md` fixture (6 lines, correct Decision join) and synthetic build_research_raw.json (bucket ordering preserved, 200-char truncation applied). |

**Score:** 11/11 ROADMAP Success Criteria verified (+1 additional plan-level truth from 02-04)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `lib/parallel_client.py` | Async Parallel AI Task API client | ✓ VERIFIED | 176 lines, exports `create_task_run`, `get_task_result`, `run_deep_research_task`, `extract_citations`. Imports cleanly, used by `pipeline/deep_research_v2.py`. |
| `lib/research_utils.py` | Shared gate/raw parsers | ✓ VERIFIED | 124 lines, both helpers present, graceful error paths, imported by both pipeline modules (identity-checked). |
| `pipeline/deep_research_v2.py` | Stage 7.5 orchestrator | ✓ VERIFIED | 240 lines, `run_deep_research_v2` exported. `_build_brief` substitutes all 10 template vars. Route filter, idempotency, Semaphore(3) all present. |
| `pipeline/deep_analysis.py` | BUILD-ONLY Stage 8 | ✓ VERIFIED | 363 lines. Zero invest references. VALID_BUILD_VERDICTS constant + assert. Imports `_format_gate_signals` from `lib.research_utils`. |
| `pipeline/digest_generator.py` | Deterministic-first Stage 9 | ✓ VERIFIED | 489 lines. `build_digest_deterministic`, `generate_synthesis_with_llm`, `collect_analyses`, `collect_pipeline_stats` all present. Legacy functions removed. Backward-compat via `post.get()` on invest_*. |
| `prompts/deep_research_brief.md` | 6-section brief + preliminary section | ✓ VERIFIED | 102 lines. All 10 vars present. Anti-anchoring framing explicit. Format instructions 800-1500 слов, Russian with English tech terms. |
| `prompts/deep_analysis.md` | i-Free context + kill signals + build-only + executive summary | ✓ VERIFIED | 146 lines. i-Free context block, 4 kill signals, 8-criterion scoring, 7-field executive summary, JSON output schema without invest_*, `{gate_signals}` + anti-anchoring blockquote. |
| `prompts/digest.md` | Narrow synthesis (key_findings + trends) | ✓ VERIFIED | 56 lines. `{summary_data}` var. JSON output contract. Explicit prohibitions on per-startup descriptions + numeric scores. |
| `run_pipeline.py` | Stage 7.5 wired + invest guard | ✓ VERIFIED | 390 lines. Import + [7.5/10] block + SystemExit guard + stage renumbering + argparse description update. |
| `config/scoring_weights.yaml` | build_mode aligned, invest_mode preserved | ✓ VERIFIED | 62 lines. Weights sum to 1.00. Thresholds match canonical taxonomy. |
| `.env.example` | PARALLEL_API_KEY documented | ✓ VERIFIED | Lines 11-16 with usage note + retry guidance. |
| `README.md` | Pipeline diagram update + invest limitation callout | ✓ VERIFIED | Line 27 diagram entry; line 33 temporary-limitation blockquote. |
| `ROADMAP.md` | Phase 2 BUILD-ONLY marker + verdict taxonomy | ✓ VERIFIED | Lines 23-48 with TEMPORARY LIMITATION (line 27), Verdict Taxonomy (line 28), Success Criteria (lines 29-41). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pipeline/deep_research_v2.py` | `lib/parallel_client.py` | `from lib.parallel_client import run_deep_research_task` | ✓ WIRED | Line 36. Called from `research_one_deep`. |
| `pipeline/deep_research_v2.py` | `2_research/{slug}/deep_research.md` | `(research_dir / "deep_research.md").write_text(header + body)` | ✓ WIRED | Line 150. Always written, even for stubs. |
| `lib/parallel_client.py` | `https://api.parallel.ai/v1/tasks/runs` | httpx async POST/GET with x-api-key header | ✓ WIRED | Lines 64-69 (POST), 89-96 (GET). `api.parallel.ai` BASE_URL present. |
| `pipeline/deep_research_v2.py` | `lib/research_utils.py` | `from lib.research_utils import _format_gate_signals, _format_raw_evidence` | ✓ WIRED | Line 37. Both called in `_build_brief`. |
| `pipeline/deep_analysis.py` | `lib/research_utils.py` | `from lib.research_utils import _format_gate_signals` | ✓ WIRED | Line 38. Called in `analyze_one`. Runtime identity check `is` with `deep_research_v2` import passes. |
| `pipeline/deep_analysis.py` | `2_research/{slug}/deep_research.md` | `deep_research_path.read_text` in analyze_one | ✓ WIRED | Line 93-97. Primary input, 8000-char budget for prompt. |
| `pipeline/deep_analysis.py` | `3_analysis/{slug}_analysis.md` | `frontmatter.Post` write with killed, kill_reason, executive_summary | ✓ WIRED | Lines 253-269. All required frontmatter fields written. |
| `prompts/deep_analysis.md` | `pipeline/deep_analysis.py` | `load_prompt("deep_analysis")` | ✓ WIRED | Line 286. Template substituted via `.replace()` chain (lines 129-141). |
| `pipeline/digest_generator.py` | `3_analysis/{slug}_analysis.md` | `frontmatter.load` reads executive_summary, killed, kill_reason | ✓ WIRED | Lines 166-207 (`collect_analyses`). All Plan 02-02 fields read. |
| `run_pipeline.py` | `pipeline/deep_research_v2.py` | `from pipeline.deep_research_v2 import run_deep_research_v2` | ✓ WIRED | Line 25; call at line 253. |
| `pipeline/digest_generator.py` | `prompts/digest.md` | `load_prompt("digest")` | ✓ WIRED | Line 277. `{summary_data}` substitution applied. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `pipeline/deep_analysis.py` analyze_one → frontmatter | `executive_summary`, `killed`, `kill_reason` | Heavy LLM result via `call_llm` on real `deep_research.md` content | Yes (when PARALLEL_API_KEY + OPENROUTER_API_KEY set — live run required to produce actual deep_research.md) | ✓ FLOWING (static path verified; live content depends on API keys — tracked as human_verification) |
| `pipeline/digest_generator.py` `_render_startup_block` | `executive_summary` | `analyses[i]["executive_summary"]` from `collect_analyses` reading 3_analysis/ frontmatter | Yes — field written by analyze_one, read by collect_analyses (grep-verified: both written and read lists match) | ✓ FLOWING |
| `pipeline/digest_generator.py` `generate_synthesis_with_llm` | `key_findings`, `trends` | LLM result from `prompts/digest.md` with `{summary_data}` payload | Yes (with sentinel fallback on failure) | ✓ FLOWING |
| `pipeline/deep_research_v2.py` `_build_brief` | `raw_evidence`, `preliminary_findings`, `gate_signals`, `website_summary` | Graceful reads of `build_research_raw.json`, `build_research.md`, `gate_build.md`, `website.md` via `lib/research_utils.py` | Yes — verified against real `2_research/21st/` fixture (gate=6 lines, raw=6034 chars, missing website → placeholder) | ✓ FLOWING |
| `run_pipeline.py` `build_ready` → Stage 7.5 | `build_gate_result.get("build_analysis_ready_slugs", [])` | Output of `run_build_gate` | Yes — existing Phase 1 contract, unchanged | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All phase 02 modules import cleanly | `python -c "from lib.parallel_client import …; from pipeline.deep_research_v2 import …; from pipeline.deep_analysis import …; from pipeline.digest_generator import …; from lib.research_utils import …"` | All imports succeed | ✓ PASS |
| Identity check: shared helper single source of truth | `assert pipeline.deep_research_v2._format_gate_signals is pipeline.deep_analysis._format_gate_signals` | True | ✓ PASS |
| Prompt `deep_research_brief.md` contains all 10 expected template variables | `load_prompt + assert all(v in p for v in [...])` | All present | ✓ PASS |
| Prompt `deep_analysis.md` contains kill signals + gate_signals + build-only + deep_research_content | `load_prompt + assert keywords` | All present | ✓ PASS |
| Prompt `digest.md` is narrow synthesis (uses `{summary_data}`, emits `key_findings`+`trends`) | `load_prompt + assert` | All present | ✓ PASS |
| VALID_BUILD_VERDICTS constant is canonical taxonomy | `assert VALID_BUILD_VERDICTS == {BUILD,PARTNER,MONITOR,SKIP}` | True | ✓ PASS |
| `analyze_one` source has no invest references | grep for `invest_total`, `invest_verdict`, `invest_scoring` in `inspect.getsource(analyze_one)` | Zero matches | ✓ PASS |
| `analyze_one` has `deep_research`, `killed`, `executive_summary`, `kill_reason`, `build_thesis` | grep source | All present | ✓ PASS |
| `run_pipeline.main` has Stage 7.5 wiring + honest invest guard | grep `run_deep_research_v2`, `7.5/10`, `invest_enabled`, `SystemExit` | All present | ✓ PASS |
| Deterministic digest builder smoke test (synthetic 3 analyses: BUILD, MONITOR, killed) | Call `build_digest_deterministic` and assert byte-for-byte exec summary insertion + killed filter + no score leakage | All assertions pass; 898-char digest; killed Gamma absent from BUILD section | ✓ PASS |
| `lib/research_utils.py` graceful missing-path handling | Call `_format_gate_signals(Path('/tmp/__nonexistent__'))` and `_format_raw_evidence(...)` | Both return explicit placeholder strings; no exceptions | ✓ PASS |
| `lib/research_utils.py` parses real 21st fixture | Call helpers on `2_research/21st/gate_build.md` + `build_research_raw.json` | Gate returns 6 lines with Decision join; raw returns 6034 chars with bucket ordering | ✓ PASS |
| Data-flow field list parity: analyze_one writes = collect_analyses reads (required subset) | `inspect.getsource` regex analysis | All 8 required fields (build_total, build_verdict, killed, kill_reason, executive_summary, recommended_market, time_to_mvp, time_to_revenue) present in both written and read sets | ✓ PASS |
| `scoring_weights.yaml` build_mode weights sum to 1.00 | `sum(w.values())` | 1.00 | ✓ PASS |
| Commits from all 4 plan SUMMARYs exist in git log | `git log --oneline` | 94ea37f, 81f2c9b, 6d29222, cca5cc4, dfc95ce, 67bfe22, d16f47f, 2c06d8c, c8542f1 all present | ✓ PASS |
| Legacy `pipeline/deep_research.py` unmodified and importable | `from pipeline.deep_research import run_deep_research` | Import succeeds (backward compat preserved) | ✓ PASS |
| Full pipeline live run produces management-ready digest | `python run_pipeline.py --html <real_export.html>` | N/A — requires PARALLEL_API_KEY, OPENROUTER_API_KEY, real DealPad export | ? SKIP (→ human_verification) |

### Requirements Coverage

All 11 ROADMAP Success Criteria for Phase 2 map to specific plans and artifacts:

| SC ID | Requirement (ROADMAP lines 29-41) | Source Plan(s) | Status | Evidence |
|-------|-----------------------------------|---------------|--------|----------|
| SC-01 | `lib/parallel_client.py` — async client for Parallel AI Task API | 02-01 | ✓ SATISFIED | Truth #1 |
| SC-02 | `pipeline/deep_research_v2.py` — Stage 7.5 deep research | 02-01, 02-04 | ✓ SATISFIED | Truth #2, #12 |
| SC-03 | `prompts/deep_research_brief.md` — research brief prompt | 02-01, 02-04 | ✓ SATISFIED | Truth #3 |
| SC-04 | Output: `2_research/{slug}/deep_research.md` with citations | 02-01 | ✓ SATISFIED | Truth #4 |
| SC-05 | Updated `pipeline/deep_analysis.py` — BUILD-ONLY + kill signals + exec summary | 02-02, 02-04 | ✓ SATISFIED | Truth #5, #12 |
| SC-06 | Updated `prompts/deep_analysis.md` | 02-02, 02-04 | ✓ SATISFIED | Truth #6 |
| SC-07 | Updated `config/scoring_weights.yaml` | 02-02 | ✓ SATISFIED | Truth #7 |
| SC-08 | Updated `pipeline/digest_generator.py` — DETERMINISTIC-FIRST | 02-03 | ✓ SATISFIED | Truth #8 |
| SC-09 | Updated `prompts/digest.md` | 02-03 | ✓ SATISFIED | Truth #9 |
| SC-10 | `PARALLEL_API_KEY` env var documented | 02-01 | ✓ SATISFIED | Truth #11 |
| SC-11 | Full pipeline run produces informative digest for management | 02-03 | ? NEEDS HUMAN | Static paths verified; live run + qualitative digest review required — tracked in human_verification |
| — | `run_pipeline.py` Stage 7.5 wiring + honest invest guard | 02-03 | ✓ SATISFIED | Truth #10 |

Note: REQUIREMENTS.md does not have a dedicated Phase 2 section for the Deep Research upgrade (R1-R8 cover Phase 1 MVP; R9+ map to Phase 3 Multi-Source + Delivery which is a different phase). ROADMAP success criteria function as the authoritative requirement list for Phase 2.

### Anti-Patterns Found

Anti-pattern scan on all files modified during Phase 2 commits (`94ea37f`, `81f2c9b`, `6d29222`, `cca5cc4`, `dfc95ce`, `67bfe22`, `d16f47f`, `2c06d8c`, `c8542f1`):

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | **No blockers found.** |

Notes:
- `return {}` / `return []` patterns exist in `_build_summary_payload` fallback and `extract_citations` empty-list returns — these are **intentional fallback/initialization**, not stubs. Never flow to user-visible output as the sole data path.
- `"(Deep research failed: ...)"` stub content is an **accepted documented limitation** (02-01 plan + `.env.example` manual-retry guidance). Stubs are distinguishable via the `is_stub` check in `research_one_deep` and surfaced to the operator as warnings.
- `"(LLM synthesis unavailable — ...)"` sentinel in `generate_synthesis_with_llm` — **accepted graceful-degradation pattern**; digest still renders 4 deterministic sections when LLM fails.
- `"(Stage 7 gate signals not available)"`, `"(Stage 5 raw evidence not available)"`, `"(website.md not available)"` — **intentional explicit placeholders** documented in `lib/research_utils.py` module docstring. Make missing-input visible in assembled prompt for debugging rather than silent empty strings.
- No TODO/FIXME/XXX/HACK markers found in Phase 2 code.
- No hollow props / always-empty state rendering.
- No `console.log`-only handlers (N/A — Python project).

### Human Verification Required

4 items require human validation beyond automated code inspection (see YAML `human_verification` block at the top).

1. **End-to-end live pipeline run** — Static verification confirms all 10 stages wire correctly; all 4 plan SUMMARYs explicitly flag that live smoke tests were NOT run (PARALLEL_API_KEY was not set at execution time). Operator must set both API keys and run against a real DealPad export to verify (a) deep_research.md is substantive not a stub, (b) executive_summary content is meaningful, (c) digest is actually management-ready.

2. **Honest invest guard live trigger** — Guard source/location verified; runtime trigger on real triage output not tested.

3. **Digest content quality (Dina's requirement)** — The Phase 2 goal phrase "informative management-ready output" is qualitative. Code mechanics confirmed perfect; writing quality of the executive summaries is what Dina actually asked for and requires her (or another non-technical reader's) judgment.

4. **Anti-anchoring effect on Parallel AI output** — Anti-anchoring is implemented via prompt framing (VALIDATE/REFUTE/EXTEND/CHALLENGE pillars + ordered raw→summary presentation + anti-anchoring blockquote in Stage 8). Whether the LLM actually challenges preliminary findings rather than parroting them requires reading multiple live outputs.

### Gaps Summary

**No gaps blocking Phase 2 goal achievement.** All 11 ROADMAP Success Criteria are satisfied at the code level. All key links are wired and data flows correctly. The canonical verdict taxonomy (`build_verdict ∈ {BUILD, PARTNER, MONITOR, SKIP}` with separate `killed: bool`) is enforced at the prompt level, at the code level (`VALID_BUILD_VERDICTS` + runtime assert), and in the digest layer (killed filter, not verdict relabelling).

Four human-verification items are raised because:

1. Phase 2's central goal — "informative management-ready digest" — is qualitative and requires non-technical stakeholder review.
2. Live API behaviour (Parallel AI response quality, anti-anchoring effect) cannot be mechanically verified from source alone.
3. Every SUMMARY.md explicitly reports no live end-to-end run executed — operator PARALLEL_API_KEY was not set during any of the 4 plan executions.

**Phase 2 is code-complete and unblocked for Phase 3.** Live validation is a one-command step (`python run_pipeline.py --html <export>` after setting two API keys) that the operator can run when convenient.

---

*Verified: 2026-04-14*
*Verifier: Claude (gsd-verifier)*

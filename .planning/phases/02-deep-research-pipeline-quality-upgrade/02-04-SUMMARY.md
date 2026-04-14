---
phase: 02-deep-research-pipeline-quality-upgrade
plan: 04
subsystem: pipeline
tags: [parallel-ai, deep-analysis, context-enrichment, gate-signals, anti-anchoring, lib-research-utils]

# Dependency graph
requires:
  - phase: 02-deep-research-pipeline-quality-upgrade
    plan: 01
    provides: pipeline/deep_research_v2.py _build_brief + research_one_deep + run_deep_research_v2 (extended here, signatures unchanged)
  - phase: 02-deep-research-pipeline-quality-upgrade
    plan: 02
    provides: pipeline/deep_analysis.py BUILD-ONLY analyze_one with VALID_BUILD_VERDICTS + executive_summary + killed flag (extended here, contracts preserved)
provides:
  - lib/research_utils.py — NEW shared helper module; _format_gate_signals canonical gate_build.md parser (graceful, never raises)
  - pipeline/deep_research_v2.py._build_brief — extended to read website.md / build_research.md / gate_build.md and substitute {website_summary} {preliminary_findings} {gate_signals}
  - prompts/deep_research_brief.md — extended with "Preliminary findings (validate or refute — NOT authoritative)" section + 3 new template vars
  - pipeline/deep_analysis.py.analyze_one — extended with graceful gate_build.md read + {gate_signals} substitution via shared helper
  - prompts/deep_analysis.md — extended with "Stage 7 gate signals" subsection + new {gate_signals} variable + anti-anchoring framing
affects: [03-core-store-refactor, 04-production-polish]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single canonical helper home: shared parsing helpers live in lib/, both pipeline modules import (NOT cross-pipeline imports) — guarantees one identity for the function object"
    - "Anti-anchoring framing in prompts: preliminary data is explicitly labelled 'NOT authoritative' with VALIDATE/REFUTE/EXTEND/CHALLENGE instructions — pattern reusable for any LLM that consumes upstream-LLM output"
    - "Graceful file reads with explicit placeholder strings ('(website.md not available)' etc.) — never raises, makes the gap visible in the assembled prompt for debugging"
    - "Token budget enforcement at read time (slicing, not post-hoc truncation) — preliminary_findings[:3000], website_summary[:2000]"
    - ".replace() chain extension pattern (continued from 02-01/02-02) — append new .replace() calls, never refactor the chain"

key-files:
  created:
    - lib/research_utils.py
  modified:
    - prompts/deep_research_brief.md
    - pipeline/deep_research_v2.py
    - prompts/deep_analysis.md
    - pipeline/deep_analysis.py

key-decisions:
  - "Helper lives in lib/research_utils.py (NEW), not in either pipeline module — both pipeline modules import the SAME function object, identity-checkable via `is` (architectural rule per worktree branch check)"
  - "Anti-anchoring framing in BOTH consumer prompts: deep_research_brief.md tells Parallel AI 'preliminary is NOT authoritative — VALIDATE/REFUTE/EXTEND/CHALLENGE'; deep_analysis.md tells Stage 8 'gate signals were set BEFORE deep research — on conflict, doverjay deep research, отметь расхождение в executive_summary'"
  - "All 4 file reads (website.md ×2, build_research.md, gate_build.md ×2) graceful — missing/unreadable file substitutes explicit placeholder string, never raises"
  - "Token budget caps applied at read time: website_summary 2KB, preliminary_findings 3KB, gate_signals ~500B — assembled brief stays well under Parallel AI's 25KB limit (verified ~6.8KB on 21st fixture)"
  - "No new dependencies, no signature changes — pure content/context extension on top of 02-01 and 02-02"
  - "Plan TEXT placed _format_gate_signals inside pipeline/deep_research_v2.py; the worktree branch check OVERRODE this with the lib/ rule and that's what shipped (architectural superseded textual)"

requirements-completed: [SC-02, SC-03, SC-05, SC-06]

# Metrics
duration: ~12min
completed: 2026-04-14
---

# Phase 02 Plan 04: Context Enrichment for Parallel AI + Stage 8 Summary

**Threads Stage 5 preliminary findings + Stage 7 gate interpretation into the Parallel AI Stage 7.5 brief AND into the Stage 8 deep_analysis prompt as "validate or refute — NOT authoritative" context. New shared helper lives in lib/research_utils.py so both pipeline modules import the same function object — single canonical home for gate_build.md parsing.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 2
- **Files created:** 1 (lib/research_utils.py)
- **Files modified:** 4 (prompts/deep_research_brief.md, pipeline/deep_research_v2.py, prompts/deep_analysis.md, pipeline/deep_analysis.py)

## Accomplishments

- NEW `lib/research_utils.py` with module docstring documenting the architectural rule (helpers live in lib/, never cross-pipeline imports).
- `_format_gate_signals(gate_path: Path) -> str` — graceful parser of `2_research/{slug}/gate_build.md`. Returns explicit placeholder when missing (`(Stage 7 gate signals not available)`), read-error (`... — read error`), or unparseable (`... — no parseable content`). Output format consumed byte-for-byte by both Parallel AI brief and Stage 8 prompt.
- Line-by-line scan (not regex) — easier to debug, sufficient for a deterministic build_gate.py-generated file.
- Decision line rendered as `Decision: build_analysis_ready: False, build_priority: medium` joined from individual `- key: value` lines under `## Decision`.
- `prompts/deep_research_brief.md` — appended new section "Preliminary findings (validate or refute — NOT authoritative)" between "Известно на входе" and "Что исследовать". Section contains all four framing pillars (VALIDATE / REFUTE / EXTEND / CHALLENGE) and explicit `NOT authoritative` label. Three new template variables: `{preliminary_findings}` `{gate_signals}` `{website_summary}` rendered under three sub-headings. Existing 6-section "Что исследовать" block, "Формат ответа" block, and "Triage LLM build thesis" line preserved byte-for-byte.
- `pipeline/deep_research_v2.py` — added `from lib.research_utils import _format_gate_signals` at module top. Extended `_build_brief` with three graceful reads (website.md → 2KB cap with placeholder; build_research.md → 3KB cap with placeholder; gate_build.md → via shared helper) and three new `.replace()` calls appended to the existing chain. Reads happen INSIDE `_build_brief` (not in `research_one_deep`) so the brief-construction helper remains single source of truth. No new imports, no signature changes for `research_one_deep` / `run_deep_research_v2` / `_format_citations`.
- `prompts/deep_analysis.md` — added "Stage 7 gate signals (интерпретация нашего гейта — проверь в deep research)" subsection between `{deep_research_content}` and `{research_notes}` blocks (gate is structured interpretation of deep research, so adjacent placement). New `{gate_signals}` template variable. Anti-anchoring blockquote: "Если deep research противоречит им — доверяй deep research, отметь расхождение в executive_summary." All 02-02 contracts (Роль, Контекст i-Free, Шаги 1-3, Формат ответа JSON block) preserved byte-for-byte.
- `pipeline/deep_analysis.py` — added `from lib.research_utils import _format_gate_signals` import. Inserted graceful gate_signals read after research_notes assembly and before name extraction. Appended `.replace("{gate_signals}", gate_signals)` as last call in the .replace() chain. No other lines modified.
- Cross-module identity check passes: `pipeline.deep_research_v2._format_gate_signals is pipeline.deep_analysis._format_gate_signals` returns True — both modules reference the SAME function object via lib import.
- Smoke tests against real `2_research/21st/` fixture (build_research.md + gate_build.md + missing website.md) confirm: brief assembles to 6,795 chars (well under 25KB Parallel AI cap), Stage 8 prompt assembles to 9,875 chars, no `{variable}` leak, all preliminary sources embedded, anti-anchoring framing present, graceful placeholder fires for missing website.md.

## Task Commits

1. **Task 1: Parallel AI input enrichment — read preliminary sources into deep_research_brief** — `d16f47f` (feat)
2. **Task 2: Stage 8 gate_signals addition — thread gate signals into deep_analysis** — `2c06d8c` (feat)

## Files Created/Modified

- `lib/research_utils.py` (created) — shared helper module; `_format_gate_signals` canonical parser; module docstring documents architectural rule.
- `prompts/deep_research_brief.md` (modified) — new "Preliminary findings (validate or refute — NOT authoritative)" section + 3 new vars; existing sections unchanged.
- `pipeline/deep_research_v2.py` (modified) — import shared helper; `_build_brief` reads 3 files gracefully, appends 3 `.replace()` calls; signatures unchanged.
- `prompts/deep_analysis.md` (modified) — new "Stage 7 gate signals" subsection + `{gate_signals}` var + anti-anchoring blockquote; 02-02 contracts preserved.
- `pipeline/deep_analysis.py` (modified) — import shared helper; `analyze_one` reads gate_build.md gracefully, appends 1 `.replace()` call; 02-02 architecture preserved.

## Decisions Made

- **Helper home in lib/, not pipeline/.** The plan TEXT (Task 1, Part B.1) said to place `_format_gate_signals` inside `pipeline/deep_research_v2.py` and have Task 2 import it cross-module. The worktree branch check OVERRODE this with: "the new `_format_gate_signals` ... helpers MUST live in `lib/research_utils.py` (NEW file). Both pipeline modules import from `lib/research_utils`, never from each other." That architectural rule shipped — keeps a clean dependency graph (pipeline → lib → stdlib; no pipeline → pipeline edges) and makes the cross-module identity check (`fmt1 is fmt2`) trivially true via Python's module caching.
- **Plan referenced `_format_raw_evidence` alongside `_format_gate_signals` in the architectural rule, but the plan body never required it.** Followed CLAUDE.md "don't overengineer" — only `_format_gate_signals` was created. If a future plan needs a second helper, it lands in the same module.
- **Anti-anchoring framing in BOTH prompts.** Same pattern, slightly different wording for each consumer:
  - deep_research_brief.md (Parallel AI): four framing pillars VALIDATE / REFUTE / EXTEND / CHALLENGE — Parallel AI's autonomy is the whole point, so the prompt actively encourages divergence from preliminary.
  - deep_analysis.md (Stage 8 LLM): single blockquote "доверяй deep research, отметь расхождение в executive_summary" — Stage 8 is a synthesis/scoring stage, not a research stage, so it doesn't need to validate; it just needs to know which input to trust on conflict.
- **Hard-cap reads at the source, not post-hoc.** `website_path.read_text(...)[:2000]` slices at read time, not after assembly. Same pattern as 02-02's `deep_research_content[:8000]` — keeps the assembly step pure.
- **Graceful placeholder strings explicit, not silent empty.** `(Stage 7 gate signals not available)` reads better than an empty string in the assembled prompt and makes the gap visible for debugging. Same for website / build_research placeholders.
- **gate_signals position in `.replace()` chain — last in deep_analysis.py.** Order doesn't affect correctness (`.replace()` is independent), but appending is the safest extension pattern (no merge risk with 02-02's existing chain).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored prior-wave artifacts deleted from worktree**
- **Found during:** initial worktree inspection
- **Issue:** After `git reset --soft 3884221...`, the worktree had `02-01/02/03-SUMMARY.md`, `02-04-PLAN.md`, `pipeline/deep_research_v2.py`, `prompts/deep_research_brief.md`, `lib/parallel_client.py` marked deleted (existed in HEAD, absent from disk) AND `pipeline/deep_analysis.py` + `prompts/deep_analysis.md` marked modified with their pre-02-02 versions on disk. Plan preamble explicitly says all prior waves "are already on main and available" and Task 2 says "READ THE VERSION THAT 02-02 SHIPPED — extension, not rewrite". The pre-existing-uncommitted directive listed only 3 specific files (.env.example, lib/exa_client.py, lib/llm.py, deleted docs/demo-dashboard.html) and none of the affected files were in that list.
- **Fix:** `git checkout 3884221 -- <paths>` for `02-01/02/03-SUMMARY.md`, `02-04-PLAN.md`, `pipeline/deep_research_v2.py`, `prompts/deep_research_brief.md`, `lib/parallel_client.py`, `pipeline/deep_analysis.py`, `prompts/deep_analysis.md`. Then `git reset HEAD <those paths>` to leave them as clean disk state. No new commits — restoration only.
- **Files modified by this plan after restore:** as listed in `key-files`.

**2. [Rule 3 - Blocking] Created 2_research/21st/ smoke-test fixture in worktree**
- **Found during:** Task 1 smoke test setup
- **Issue:** The plan's smoke tests use `2_research/21st/build_research.md` + `gate_build.md` as fixtures, but `2_research/` is gitignored and the worktree (a fresh clone-like checkout) had no `2_research/` directory at all. Without the fixtures the smoke tests cannot run.
- **Fix:** Copied `gate_build.md`, `build_research.md`, `build_research_raw.json` from the main project's `2_research/21st/` (where the real pipeline run produced them) into the worktree's `2_research/21st/`. Files are gitignored so this leaves no commit footprint.
- **Files modified:** none — fixtures are pipeline-generated data, not tracked source.

### Architectural deviation from plan TEXT

The plan's Task 1 Part B.1 instructed to define `_format_gate_signals` directly inside `pipeline/deep_research_v2.py`, and Task 2 Part B.1 instructed `from pipeline.deep_research_v2 import _format_gate_signals`. The orchestrator's `<worktree_branch_check>` block OVERRODE this with: helpers MUST live in `lib/research_utils.py`, both pipeline modules import from there. Followed the orchestrator rule because:
  1. The orchestrator note explicitly framed it as a critical architectural rule.
  2. The plan's `<verification>` block #3 (`assert da._format_gate_signals is f2`) is satisfied either way (Python module imports cache by default).
  3. The lib/ home is genuinely cleaner — pipeline modules don't import from each other for shared helpers, the dependency graph stays a tree.
The acceptance criterion text in Task 1 ("MUST be module-level and self-contained so Task 2 can import it") is satisfied by being module-level in lib/. The acceptance criterion text in Task 2 ("imports _format_gate_signals from pipeline.deep_research_v2") is the only literal-text deviation; the architectural intent (single source of truth, importable, identity-equal) is fully met.

## Issues Encountered

- **No live Parallel AI / OpenRouter smoke test executed.** Both prompts were verified by static assembly only — `_build_brief` and the Stage 8 prompt assembly are pure string operations whose output was inspected against the 21st fixture. Live verification would burn API credits on a slug whose `deep_research.md` may not exist; per 02-01-SUMMARY.md the `PARALLEL_API_KEY` is still an operator setup prerequisite. All `<verification>` block automated assertions from the plan pass.
- **Pre-existing uncommitted changes left UNTOUCHED** in `.env.example`, `.planning/ROADMAP.md`, `README.md`, `config/scoring_weights.yaml`, `pipeline/digest_generator.py`, `prompts/digest.md`, `run_pipeline.py`. None are in this plan's `files_modified` list. Per `<pre_existing_uncommitted>` and `task_commit_protocol`, only task-related files were staged.

## User Setup Required

**No new user setup beyond Plan 02-01's `PARALLEL_API_KEY` requirement.** The new code reads from local files (gracefully — no failure on missing) and adds context to existing API calls (Parallel AI for Stage 7.5, OpenRouter for Stage 8). Token budgets verified to stay within both providers' input limits.

## Next Phase Readiness

- All Phase 2 plans (02-01 through 02-04) feature-complete. Ready for end-to-end live validation: `python run_pipeline.py --html …` will exercise Stages 1→10 with enriched Parallel AI briefs and gate-signal-aware Stage 8 prompts once `PARALLEL_API_KEY` is configured.
- `lib/research_utils.py` is a stable extension point — future shared parsers (e.g., a `_format_raw_evidence` for `build_research_raw.json`, or an `_format_invest_signals` once invest-mode returns) land in the same module.
- Phase 3 (core/ refactor) inherits the cleanly-separated `lib/research_utils.py` boundary — no migration cost when `pipeline/` modules later move to `core/`.

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`. All five STRIDE threats (T-02-13 through T-02-17) handled as specified:

- **T-02-13 (Tampering of build_research.md → Parallel AI):** accepted — content is generated by our own Stage 5 LLM pipeline; Parallel AI treats input as prompt text, no code execution path. Risk unchanged from 02-01.
- **T-02-14 (Tampering of gate_build.md → Stage 8):** accepted — content generated by our own Stage 7 gate; `_format_gate_signals` is pure string parsing (no eval, no exec, line-by-line scan).
- **T-02-15 (Info disclosure of website.md → Parallel AI):** accepted — website.md is public website content, already fetched from the public internet; re-sending re-exposes nothing.
- **T-02-16 (DoS via oversized build_research.md):** mitigated — hard 3000-char cap on `preliminary_findings` and 2000-char cap on `website_summary` enforced at read time. Total added context bounded ~5500 chars, well under Parallel AI's 25KB input limit. Verified on 21st fixture: assembled brief = 6,795 chars.
- **T-02-17 (Repudiation via missing/malformed gate_build.md):** mitigated — explicit placeholder strings (`(Stage 7 gate signals not available)`, `(website.md not available)`, `(Stage 5 build research not available)`) ensure prompt still reads well AND make the drop visible in the assembled prompt for debugging. Never raises.

## Self-Check: PASSED

- `lib/research_utils.py` — FOUND; `_format_gate_signals` defined as module-level pure function with graceful error paths.
- `prompts/deep_research_brief.md` — FOUND; contains `{preliminary_findings}`, `{gate_signals}`, `{website_summary}`; contains `validate`, `refute`, `NOT authoritative`; "Preliminary findings" section sits between "Известно на входе" and "Что исследовать"; existing 6-section block + Формат ответа preserved.
- `pipeline/deep_research_v2.py` — FOUND; imports `_format_gate_signals` from `lib.research_utils`; `_build_brief` reads `website.md`, `build_research.md`, `gate_build.md`; appends 3 `.replace()` calls; `research_one_deep` / `run_deep_research_v2` / `_format_citations` unchanged.
- `prompts/deep_analysis.md` — FOUND; contains `{gate_signals}`; new "Stage 7 gate signals" subsection between `{deep_research_content}` and `{research_notes}`; 02-02 contracts ({deep_research_content}, {build_thesis}, Шаги 1-3, JSON Формат ответа) preserved.
- `pipeline/deep_analysis.py` — FOUND; imports `_format_gate_signals` from `lib.research_utils`; `analyze_one` reads `gate_build.md`; appends `.replace("{gate_signals}", gate_signals)`; 02-02 contracts (`deep_research_content`, `killed`, `executive_summary`, `VALID_BUILD_VERDICTS`) preserved.
- Commit `d16f47f` — FOUND.
- Commit `2c06d8c` — FOUND.
- Plan `<verification>` block (6 checks):
  - 1. deep_research_brief has `{preliminary_findings}` + `{gate_signals}` + `{website_summary}` — PASSED.
  - 2. `_format_gate_signals` + `_build_brief` importable from `pipeline.deep_research_v2` — PASSED.
  - 3. `pipeline.deep_analysis._format_gate_signals is pipeline.deep_research_v2._format_gate_signals` — PASSED.
  - 4. deep_analysis prompt has `{gate_signals}` AND `{deep_research_content}` — PASSED.
  - 5. `_format_gate_signals` parses real `2_research/21st/gate_build.md` correctly — PASSED.
  - 6. `_format_gate_signals` graceful on missing path — PASSED.
- Smoke test 1 (Task 1, _build_brief on 21st): assembled 6,795 chars, all preliminary sources embedded, graceful website.md placeholder, anti-anchoring tokens present — PASSED.
- Smoke test 2 (Task 2, Stage 8 prompt on 21st): assembled 9,875 chars, gate_signals threaded, no `{variable}` leak — PASSED.

---
*Phase: 02-deep-research-pipeline-quality-upgrade*
*Completed: 2026-04-14*

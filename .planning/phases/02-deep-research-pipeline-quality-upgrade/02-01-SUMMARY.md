---
phase: 02-deep-research-pipeline-quality-upgrade
plan: 01
subsystem: pipeline
tags: [parallel-ai, httpx, async, deep-research, stage-7.5, citations]

# Dependency graph
requires:
  - phase: 01-mvp-dealpad-pipeline
    provides: BaseScout/idea frontmatter, build gate slug output, prompt-loading convention, lib/llm, lib/utils, route-filtered research pattern (build_research.py)
provides:
  - lib/parallel_client.py — async Parallel AI Task API client (create / get / convenience)
  - pipeline/deep_research_v2.py — Stage 7.5 deep research orchestrator (slug list → deep_research.md per startup)
  - prompts/deep_research_brief.md — 6-section Russian research brief with build_thesis hypothesis
  - .env.example — PARALLEL_API_KEY documented with stub-retry guidance
affects: [02-02-deep-analysis-update, 02-03-digest-update, 03-core-store-refactor, 04-production-polish]

# Tech tracking
tech-stack:
  added: [parallel-ai-task-api]
  patterns:
    - "Thin httpx async wrappers over third-party APIs (matches lib/exa_client.py)"
    - "Two-level iteration for Parallel AI output.basis citations extraction"
    - ".replace() for prompt template substitution (JSON-brace compatibility)"
    - "Stub-on-failure pattern: run_deep_research_task never raises, writes (Deep research failed: ...) stub; idempotency check skips stubs on rerun"
    - "Canonical _v2 suffix for Stage 7.5 module (legacy deep_research.py untouched)"

key-files:
  created:
    - lib/parallel_client.py
    - pipeline/deep_research_v2.py
    - prompts/deep_research_brief.md
  modified:
    - .env.example

key-decisions:
  - "Use httpx async wrapper (not parallel Python SDK) — minimal deps, matches project pattern"
  - "Semaphore(3) for concurrency — Parallel AI handles rate limits server-side, client-side cap conservative"
  - "Processor tier = core ($0.025/run) — quality default per 02-CONTEXT.md"
  - "build_thesis in brief as hypothesis-to-validate, not to confirm — LLM instructed to challenge with data"
  - "Failed API calls write stub file; retry requires manual delete (auto-retry deferred to Phase 4)"
  - "Legacy pipeline/deep_research.py preserved unchanged; _v2 is canonical Phase 2 name"

patterns-established:
  - "Stub-write-on-failure: return fallback dict instead of raising so pipeline does not block; caller writes stub file; idempotency check prevents accidental re-run consuming new API credits"
  - "Citations normalization: flatten output.basis via two-level iteration into {url, title, excerpt} list; render under ## Источники"
  - "Prompt variable substitution via .replace() chain (not .format()) to survive literal JSON braces in prompts"

requirements-completed: [SC-01, SC-02, SC-03, SC-04, SC-10]

# Metrics
duration: 3min
completed: 2026-04-14
---

# Phase 02 Plan 01: Deep Research Client + Stage 7.5 Summary

**Async Parallel AI client and Stage 7.5 orchestrator that runs autonomous deep research on build-gate-passed startups and writes rich citation-backed reports to 2_research/{slug}/deep_research.md.**

## Performance

- **Duration:** ~3 min (code authoring; does not include smoke test against live API — see Issues Encountered)
- **Started:** 2026-04-14T11:18:07Z
- **Completed:** 2026-04-14T11:21:20Z
- **Tasks:** 2
- **Files created:** 3
- **Files modified:** 1

## Accomplishments
- Async httpx-based Parallel AI Task API client (`lib/parallel_client.py`) exporting `create_task_run`, `get_task_result`, `run_deep_research_task`.
- Two-level citations extraction (`extract_citations`) — correctly walks nested basis-items, avoiding the flat-list KeyError pitfall documented in 02-RESEARCH.md.
- Stage 7.5 orchestrator (`pipeline/deep_research_v2.py`) with route filtering (build/both), idempotency on `deep_research.md` existence, Semaphore(3) concurrency cap, and per-slug stub-write on failure.
- Russian-language 6-section research brief prompt with `build_thesis` threaded as a hypothesis-to-validate (triage-LLM output, falls back to explicit placeholder when missing).
- `.env.example` documents `PARALLEL_API_KEY` with stub-retry guidance visible to operators.
- Legacy `pipeline/deep_research.py` untouched — backward compat preserved per 02-CONTEXT decision.

## Task Commits

1. **Task 1: async Parallel AI Task API client** — `94ea37f` (feat)
2. **Task 2: Stage 7.5 deep research pipeline module + brief prompt** — `81f2c9b` (feat)

## Files Created/Modified

- `lib/parallel_client.py` (created) — httpx async client for https://api.parallel.ai/v1; `create_task_run`, `get_task_result`, convenience `run_deep_research_task` with two-level citations extraction; never raises in the convenience path.
- `pipeline/deep_research_v2.py` (created) — Stage 7.5 entry point `run_deep_research_v2(slugs)`; research_one_deep builds brief via .replace(), calls Parallel AI, writes `2_research/{slug}/deep_research.md` with `## Источники` section.
- `prompts/deep_research_brief.md` (created) — 6-section research brief (суть/TAM/конкуренты/валидация/build/география); template variables `{name}`, `{url}`, `{description}`, `{round_raw}`, `{category}`, `{build_thesis}`.
- `.env.example` (modified) — added `PARALLEL_API_KEY` with inline comment documenting stub-on-failure behavior and manual-delete retry.

## Decisions Made

- **httpx vs parallel SDK:** chose httpx — already a project dep, matches `lib/exa_client.py` pattern of thin API wrappers, avoids an extra dependency.
- **Semaphore(3) concurrency:** Parallel AI handles rate limiting server-side; 3 is a conservative client-side cap that matches `build_research.py` proportions (2-3 concurrent).
- **Stub-write on failure:** consistent with `build_research.py` pattern ("(LLM synthesis failed)") — pipeline never blocks on one bad startup, and the idempotency file-exists check prevents accidental re-runs from burning API credits.
- **`_v2` is canonical:** per 02-CONTEXT.md, `deep_research_v2.py` is the permanent Phase 2 name — legacy `deep_research.py` stays untouched; rename happens only during Phase 4 cleanup.

## Deviations from Plan

None — plan executed exactly as written. No auto-fixes, no architectural changes, no scope adjustments.

## Issues Encountered

- **Smoke test against live Parallel AI API not run.** The plan's smoke test requires `PARALLEL_API_KEY` to be set in `.env` to hit https://api.parallel.ai/v1 against a real build-gate-passed slug (e.g. `deeptrace`, `approxima`). At execution time, `.env` had no `PARALLEL_API_KEY` entry — per `<authentication_gates>`, this is an operator setup step, not a code defect. The error path was verified locally with an empty key (HTTP 401 → stub dict returned; no exception propagated), confirming the module's accepted-limitation behavior works end to end. Once the operator adds `PARALLEL_API_KEY` to `.env`, the smoke test can be re-run; a successful live call will produce `2_research/{slug}/deep_research.md` with a real `## Источники` section and substantive content (>500 chars). All automated verification checks in the plan's `<verification>` block passed.
- **Pre-existing uncommitted changes in worktree.** At start, `.planning/STATE.md`, `lib/exa_client.py`, `lib/llm.py`, and `docs/demo-dashboard.html` had unstaged modifications/deletions predating this plan. Per `task_commit_protocol`, only task-related files were staged — the unrelated changes remain untouched for the orchestrator / user to handle.

## User Setup Required

**Parallel AI API key required to run Stage 7.5.**
- Add `PARALLEL_API_KEY=<key>` to `.env` (format documented in `.env.example`).
- Source: Parallel AI dashboard → API Keys.
- Verification after setup:
  ```bash
  cd /Users/eli/Documents/PythonProjects/StartupScanner && \
    .venv/bin/python -c "
  import asyncio
  from pipeline.deep_research_v2 import run_deep_research_v2
  r = asyncio.run(run_deep_research_v2(['deeptrace']))
  print(r)
  " && \
    test -f 2_research/deeptrace/deep_research.md && \
    head -20 2_research/deeptrace/deep_research.md
  ```

## Next Phase Readiness

- Stage 7.5 code complete — ready to be wired into `run_pipeline.py` between the build gate and Stage 8 (scheduled for a later plan in this phase).
- Output contract fixed: `2_research/{slug}/deep_research.md` with a `## Источники` section — Stage 8 (02-02 Deep Analysis Update) can read this as its primary research input.
- `build_thesis` field is already consumed by triage (per Phase 01-08 work) — the brief wires it through without requiring upstream changes.
- Canonical module naming (`_v2`) documented in module docstring and 02-CONTEXT.md — no ambiguity for future phases.
- Blocker for live end-to-end run: operator must set `PARALLEL_API_KEY` in `.env` (see User Setup Required).

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`. Parallel AI interaction stays behind a single module boundary (`lib/parallel_client.py`); API key is loaded via `os.getenv` and never written to files or log lines (T-02-01 mitigated); HTTP errors surface the status code but not the key (T-02-04 mitigated).

## Self-Check: PASSED

- `lib/parallel_client.py` — FOUND
- `pipeline/deep_research_v2.py` — FOUND
- `prompts/deep_research_brief.md` — FOUND
- `.env.example` PARALLEL_API_KEY — FOUND
- Commit `94ea37f` — FOUND
- Commit `81f2c9b` — FOUND
- All 5 `<verification>` checks in PLAN — PASSED
- Legacy `pipeline/deep_research.py` — unmodified (import verified)

---
*Phase: 02-deep-research-pipeline-quality-upgrade*
*Completed: 2026-04-14*

---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: 09
title: "Dual Exa-Powered Research and Gate Modules"
subsystem: pipeline
tags: [exa, research, gate, invest, build, dual-track]
dependency_graph:
  requires: [01-08]
  provides: [invest_research, build_research, invest_gate, build_gate, exa_client]
  affects: [run_pipeline.py]
tech_stack:
  added: [exa-py]
  patterns: [asyncio.to_thread for sync SDK, track-specific research, dual gate evaluation]
key_files:
  created:
    - lib/exa_client.py
    - pipeline/invest_research.py
    - pipeline/build_research.py
    - pipeline/invest_gate.py
    - pipeline/build_gate.py
    - prompts/invest_research.md
    - prompts/build_research.md
    - prompts/invest_gate.md
    - prompts/build_gate.md
  modified:
    - requirements.txt
    - .env.example
    - config/triage.yaml
decisions:
  - "exa-py SDK is synchronous; wrapped with asyncio.to_thread() in pipeline modules"
  - "Invest gate uses 2/3 evidence threshold from existing config; build gate uses CIS gap OR replicable+demand logic"
  - "Existing deep_research.py and research_gate.py left untouched as legacy/fallback"
metrics:
  duration_seconds: 373
  completed: "2026-04-10T14:55:24Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 9
  files_modified: 3
---

# Phase 01 Plan 09: Dual Exa-Powered Research and Gate Modules Summary

Exa web search client plus track-specific invest/build research and gate modules replacing unified LLM-only approach with real web data.

## What Was Done

### Task 1: Exa client + invest/build research modules (3624433)

Created `lib/exa_client.py` as a thin wrapper around exa-py SDK -- `exa_search()` returns `list[dict]` with title/url/text, never raises (returns empty list on failure). EXA_API_KEY loaded from .env only, never logged.

Created `pipeline/invest_research.py` with `run_invest_research(slugs)` -- runs Exa queries for `"{name}" founders team` and `"{name}" funding traction revenue`, scrapes website, synthesizes via LLM into `invest_research.md` in `2_research/{slug}/`. Route-filtered (invest/both only), idempotent.

Created `pipeline/build_research.py` with `run_build_research(slugs)` -- runs Exa queries for CIS competitors (`{category} Россия`, `{category} аналог CIS`) and OSS alternatives (`{name} open source alternative github`), synthesizes into `build_research.md`. Route-filtered (build/both only), idempotent.

Created corresponding prompts in `prompts/invest_research.md` and `prompts/build_research.md` with calibration notes about real web data.

Added `exa-py>=1.0` to requirements.txt and `EXA_API_KEY` to .env.example.

### Task 2: Dual gate modules (43d0405)

Created `pipeline/invest_gate.py` with `run_invest_gate(slugs)` -- evaluates invest_research.md via LLM for 3 boolean signals (has_team_data, has_traction_data, has_competitive_context). Uses existing `research_gate.invest_evidence_threshold` (2/3) from config. Writes `gate_invest.md`, updates idea frontmatter with `invest_analysis_ready`.

Created `pipeline/build_gate.py` with `run_build_gate(slugs)` -- evaluates build_research.md via LLM for 5 boolean signals (cis_gap_confirmed, replicable_confirmed, oss_base_available, market_demand_signals, clear_localization_path). Ready if `cis_gap_confirmed` OR (`replicable_confirmed` AND `market_demand_signals`). Writes `gate_build.md`, updates idea frontmatter with `build_analysis_ready` and `build_priority`.

Created prompts `prompts/invest_gate.md` and `prompts/build_gate.md` with calibration notes. Added `build_gate` config section to `config/triage.yaml`.

Both gate modules: LLM outputs coerced to bool, fallback dict (all False) on failure, as required by threat model T-08-04.

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

All 10 plan verifications passed:
1. All 5 library/pipeline modules import cleanly
2. All 4 prompts exist with correct template variables
3. compute_build_ready logic: True for cis_gap, True for replicable+demand, False otherwise
4. compute_invest_ready logic: True for 2/3, False for 1/3
5. deep_research.py and research_gate.py NOT modified

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 3624433 | Exa client, invest/build research modules and prompts |
| 2 | 43d0405 | Dual invest/build gate modules and prompts |

## Self-Check: PASSED

All 9 created files exist. Both commit hashes verified. SUMMARY.md exists at correct path.

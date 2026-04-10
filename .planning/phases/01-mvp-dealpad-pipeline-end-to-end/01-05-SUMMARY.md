---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: "05"
subsystem: pipeline
tags: [digest, orchestrator, pipeline, cli, async, llm, weekly-report]
dependency_graph:
  requires:
    - lib/llm.py
    - lib/utils.py
    - prompts/digest.md
    - scouts/dealpad_parser.py
    - pipeline/prefilter.py
    - pipeline/quick_score.py
    - pipeline/deep_research.py
    - pipeline/deep_analysis.py
    - 3_analysis/ (reads *_analysis.md files)
  provides:
    - pipeline/digest_generator.py
    - run_pipeline.py
    - digests/{YYYY}-W{WW}_weekly.md (runtime output)
  affects:
    - end users (single-command pipeline entry point)
tech_stack:
  added: []
  patterns:
    - LLM-first with manual template fallback for digest generation
    - argparse CLI with required --html path argument and existence check
    - load_dotenv() at module top before pipeline imports
    - asyncio.run() as single event loop entry point
    - Per-step timing printed with time.time()
    - ISO week number via datetime.date.isocalendar()[1] for digest filename
    - Counter for trend category frequency analysis
key_files:
  created:
    - pipeline/digest_generator.py
    - run_pipeline.py
  modified: []
decisions:
  - "LLM-first digest with manual fallback: tries OPENROUTER_MODEL_LIGHT first, falls back to build_digest_manually() if result is absent or < 200 chars — digest is always produced regardless of LLM availability"
  - "Digest filename uses ISO week number (isocalendar()[1]) formatted as W{WW} — matches CLAUDE.md file naming spec"
  - "load_dotenv() placed at module level in run_pipeline.py before pipeline imports — ensures env vars are loaded before any module-level code in lib/llm.py reads them"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 1 Plan 5: Digest Generator and Pipeline Orchestrator Summary

## One-liner

Weekly digest generator with LLM-first + manual fallback producing 6-section Markdown report, wired into a single `run_pipeline.py --html` CLI that chains all 6 pipeline steps with per-step timing and a final summary.

## What Was Built

### Task 1: Digest generator (pipeline/digest_generator.py)

- `collect_pipeline_stats()` — counts total ideas, archived, scored (have invest_score), shortlisted (invest >= 6 OR build >= 6), and fully analyzed (3_analysis/*_analysis.md count)
- `collect_analyses()` — reads all `*_analysis.md` files from `3_analysis/`, loads YAML frontmatter (name, url, invest_total, build_total, invest_verdict, build_verdict, round_raw) plus full content text, falls back to matching idea file for category; returns list sorted by invest_total descending
- `build_digest_data()` — serializes stats + analyses to JSON string for LLM prompt substitution
- `generate_digest_with_llm()` — loads `prompts/digest.md`, substitutes `{analysis_data}`, calls light LLM model (json_mode=False, temperature=0.3) when fewer than 50 analyses; returns empty string on failure so fallback kicks in
- `build_digest_manually()` — pure-Python Markdown builder with all 6 required sections: Pipeline Summary (bullet list with parsed/filtered/scored/shortlisted/analyzed counts), INVEST Candidates (per-startup blocks with round/category/invest rationale/key risk), WATCH List (Markdown table), BUILD Opportunities (per-startup blocks with CIS adaptation), Trends This Week (Counter of top 5 categories), All Scored Startups (full sorted table)
- `run_digest()` — creates `digests/` dir, calls LLM path, falls back to manual if result < 200 chars, writes `digests/{YYYY}-W{WW}_weekly.md`
- `__main__` block for standalone execution

### Task 2: Pipeline orchestrator (run_pipeline.py)

- `load_dotenv()` at module level — env vars loaded before any pipeline imports
- Imports all 6 pipeline functions: `parse_dealpad`, `run_prefilter`, `run_quick_score`, `run_deep_research`, `run_deep_analysis`, `run_digest`
- `async def main(html_path)` — prints banner, runs all 6 steps sequentially with `[1/6]...[6/6]` progress labels and per-step timing via `time.time()`
- Final summary block prints counts from each step's return dict (parsed, filtered passed/rejected, scored/shortlisted, researched, analyzed, digest path)
- `argparse` CLI with `--html` required argument; validates path exists before running, prints error to stderr and `sys.exit(1)` if missing
- `asyncio.run(main(args.html))` as single event loop entry point

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | ffed445 | feat(01-05): implement weekly digest generator |
| Task 2 | 88a3454 | feat(01-05): implement run_pipeline.py end-to-end orchestrator |

## Self-Check: PASSED

- `pipeline/digest_generator.py` confirmed present on disk
- `run_pipeline.py` confirmed present on disk
- Commit ffed445 confirmed in git history
- Commit 88a3454 confirmed in git history
- `python run_pipeline.py --help` exits 0 and shows `--html` argument
- All 6 pipeline imports verified in run_pipeline.py source
- All 6 digest sections verified in build_digest_manually() output

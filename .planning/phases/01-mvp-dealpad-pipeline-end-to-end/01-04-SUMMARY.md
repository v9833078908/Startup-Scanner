---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: "04"
subsystem: pipeline
tags: [deep-research, deep-analysis, scraping, llm, scoring, async, pipeline]
dependency_graph:
  requires:
    - lib/llm.py
    - lib/scraper.py
    - lib/utils.py
    - prompts/deep_analysis.md
    - config/scoring_weights.yaml
    - pipeline/quick_score.py
  provides:
    - pipeline/deep_research.py
    - pipeline/deep_analysis.py
  affects:
    - run_pipeline.py (calls run_deep_research, run_deep_analysis)
    - pipeline/digest.py (reads 3_analysis/ files for digest generation)
tech_stack:
  added: []
  patterns:
    - Website scraping via lib/scraper.scrape_website with async httpx
    - LLM research synthesis with json_mode=True and training-data disclaimer
    - RESEARCH_DIR / slug / {website.md, web_research.md} two-file research pattern
    - Prompt template variable substitution via str.replace (no third-party templating)
    - compute_weighted_score handles both plain int scores and {score, rationale} dicts
    - determine_verdict sorts thresholds descending — config-driven, not hardcoded
    - YAML frontmatter on analysis files via frontmatter.Post
    - Stub post fallback when idea file not found — analysis proceeds regardless
key_files:
  created:
    - pipeline/deep_research.py
    - pipeline/deep_analysis.py
  modified: []
decisions:
  - "compute_weighted_score accepts both plain numeric scores and {score, rationale} dicts — deep_analysis.md prompt returns the latter but plain ints are also valid input"
  - "determine_verdict sorts thresholds dict descending by value at call time — works correctly with any config shape, no assumptions about key ordering"
  - "run_deep_analysis creates stub frontmatter.Post when no matching idea file found — research-only slugs (manually placed) are still analyzed without crashing"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 1 Plan 4: Deep Research and Deep Analysis Summary

## One-liner

Async pipeline stages 4 and 5: website scraping + LLM training-data research synthesis into `2_research/{slug}/`, then config-driven weighted invest/build scoring via heavy model into `3_analysis/{slug}_analysis.md` with YAML frontmatter verdicts.

## What Was Built

### Task 1: Deep research module (pipeline/deep_research.py)

- `research_one(post, slug)` — creates `2_research/{slug}/`, scrapes startup URL via `lib/scraper.scrape_website`, writes `website.md` with scraped content, calls light LLM model to synthesize research into 6 sections (summary, founders, business_model, competitors, traction, risks), writes `web_research.md` with explicit disclaimer: "NOT based on real-time web search"
- `run_deep_research(shortlist)` — if no shortlist provided, auto-detects candidates by scanning `1_ideas/` for ideas with `invest_score >= 6 OR build_score >= 6`; skips slugs that already have `web_research.md` (idempotent); runs all with `asyncio.gather(return_exceptions=True)`; prints progress and summary counts
- `if __name__ == "__main__"` block for standalone execution

### Task 2: Deep analysis module (pipeline/deep_analysis.py)

- `load_weights()` — reads `config/scoring_weights.yaml` via yaml.safe_load
- `compute_weighted_score(scores, weights)` — multiplies each criterion score by its weight, handles both plain numeric scores and `{score: N, rationale: "..."}` dicts (matches deep_analysis.md prompt output format), returns rounded float
- `determine_verdict(score, thresholds)` — sorts thresholds descending, returns first label where score >= threshold; fully config-driven from scoring_weights.yaml
- `analyze_one(post, slug, research_dir, prompt_template, weights)` — loads `website.md` and `web_research.md` from research dir, substitutes 6 template variables into `prompts/deep_analysis.md`, calls heavy LLM model (temperature=0.2), computes weighted totals and verdicts, writes `3_analysis/{slug}_analysis.md` with YAML frontmatter (name, url, invest_total, build_total, invest_verdict, build_verdict, analyzed_at) and full markdown body with per-criterion scores + rationales, flags, CIS adaptation, risks, next steps
- `run_deep_analysis(slugs)` — if no slugs provided, auto-detects from `2_research/` subdirs that have `web_research.md`; skips already-analyzed slugs (idempotent); stubs missing idea files so analysis is not blocked; runs with `asyncio.gather(return_exceptions=True)`

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 1613743 | feat(01-04): implement deep research pipeline stage |
| Task 2 | af8f594 | feat(01-04): implement deep analysis pipeline stage |

## Self-Check: PASSED

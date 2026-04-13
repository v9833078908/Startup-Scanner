# Session Summary — 2026-04-10 — Startup Scouting Pipeline

## Project

Scouting pipeline for iFree (tech company, not fund). Two modes: **Invest** ($30K-$300K seed) + **Build** (copy/adapt ideas for CIS). Source: DealPad Telegram export (424 startups). Demo: April 15, 2026.

Architecture: `1_ideas/` → `2_research/` → `3_analysis/` → `digests/`. No DB. Markdown + scripts + git. LLM via OpenRouter.

## What Was Done

### Phase 1 MVP — Executed (plans 01-01..01-05)
5 plans, 5 waves, all verified.

| Plan | Built |
|------|-------|
| 01-01 | venv, 8 deps, 10 dirs, configs, lib/llm+scraper+utils, 3 prompts, THESIS.md, SCHEMA.md |
| 01-02 | DealPad parser (424 ideas), pre-filter (keyword match) |
| 01-03 | LLM quick score (async, OpenRouter) |
| 01-04 | Deep research (scrape) + deep analysis (10+8 criteria weighted scoring) |
| 01-05 | Digest generator (LLM + fallback), run_pipeline.py orchestrator |

### Plan 01-06 — Executed (review-driven rewrite)
Replaced keyword pre-filter with LLM classification. Replaced opaque 1-10 quick scores with formula from structured LLM answers. Added `--reset`, config-driven thresholds, graceful LLM failure handling.

### Plan 01-07 — Planned (not yet executed)
5-stage funnel redesign. Triage + research gate + deferred scoring. See below.

## Key Decisions

| Decision | Why |
|----------|-----|
| OpenRouter via openai SDK (`base_url` override) | Unified interface, model switching via .env |
| Models: Gemini 2.5 Flash (light), Claude Sonnet 4.6 (heavy) | Cost vs quality tradeoff |
| `.replace()` not `.format()` for prompts | Prompts contain literal JSON `{}` |
| Round size = scoring FACTOR, not eligibility gate | $30K-$300K is iFree's check, not round cutoff |
| unknown founder = neutral, not negative | Data absence ≠ bad evidence |
| `invest_score`/`build_score` deferred to Stage 5 | Early stage can't judge — only triage |
| Build triage: rare signals (ru_gap, oss, cross_sell) at research gate | Need enriched data to detect |

## Pipeline Runs — Findings

**Run 1 (original, plan 01-01..05):**
424 parsed → 274 keyword-rejected → 150 scored → 124 shortlisted (83%) → problem: LLM clusters at 5-6

**Run 2 (01-06, LLM classify + formula):**
424 → 118 hard reject → 306 classified → 304 scored → **191 shortlisted (63%)** → 190 researched → 35 analyzed (stopped)

**Root causes identified:**
- Build formula: B2B software auto-scores 8-9/10 (structural floor too high)
- `cis_transferable: "high"` for 96% (LLM positivity bias)
- No gate between research → analysis (all researched → heavy model)

## Current State (Plan 01-07 pending)

```
424 DealPad ideas
├── 118 archived (hard reject)
├── 306 in 1_ideas/ (classified + scored with 01-06 formula)
│   ├── 190 researched in 2_research/
│   │   └── 35 analyzed in 3_analysis/
│   └── 0 digests
```

## 01-07: Pending Architecture Change

```
Stage 1: Hard filter (free) → ~300
Stage 2: LLM classify (cheap) → ~300
Stage 3: TRIAGE (binary questions, calibrated) → 30-60
Stage 4: Deep research (scrape) → 30-60
Stage 4.5: RESEARCH GATE (rare signals) → 10-20
Stage 5: Heavy analysis (REAL scores) → 10-20
Stage 6: Digest
```

Key changes:
- `pipeline/triage.py` replaces `quick_score.py` — outputs `invest_priority`/`build_candidate`, NOT scores
- `pipeline/research_gate.py` — new Stage 4.5, detects `ru_gap`, `oss_commercializable`, `cross_sell_fit`, `underserved_niche`
- Anti-bias: base-rate anchors, few-shot with negatives, descending order, binary questions
- `invest_score`/`build_score` only in `3_analysis/` (Stage 5)

## Roadmap

| Phase | Status |
|-------|--------|
| 1: MVP DealPad Pipeline | ✓ Complete (+ 01-06 rewrite + 01-07 planned) |
| 2: Scout Framework + 6 Simple Parsers | Not started |
| 3: Auth-Based + Complex Parsers (6) | Not started |
| 4: Research Enrichment Pipeline | Not started |
| 5: Full Scoring & Report Suite | Not started |
| 6: Delivery & Automation | Not started |
| 7: Advanced Features & Polish | Not started |

## Files Structure

```
StartupScanner/
├── CLAUDE.md, THESIS.md, SCHEMA.md
├── .env (API keys)
├── config/ (filters.yaml, scoring_weights.yaml, scoring_formula.yaml, triage.yaml)
├── prompts/ (classify.md, quick_score.md, deep_analysis.md, digest.md, triage.md, research_gate.md)
├── lib/ (llm.py, scraper.py, utils.py)
├── scouts/ (dealpad_parser.py)
├── pipeline/ (prefilter.py, quick_score.py, deep_research.py, deep_analysis.py, digest_generator.py)
├── run_pipeline.py (orchestrator, --reset, --html)
├── data/ChatExport_2026-04-10/messages.html (424 posts)
├── 1_ideas/, 2_research/, 3_analysis/, _archive/, digests/
└── .planning/ (GSD: PROJECT, ROADMAP, REQUIREMENTS, STATE, phases/)
```

**28 commits. Pushed to github.com/v9833078908/Startup-Scanner.**

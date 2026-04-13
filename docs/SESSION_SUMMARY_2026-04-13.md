# Session Summary — 2026-04-13

## What Was Done

### Plan 01-07: 5-Stage Triage Funnel (executed via GSD)
- `pipeline/triage.py` — binary evidence signals (has_product_evidence, has_founder_signal)
- `pipeline/research_gate.py` — Stage 4.5, rare build signal detection
- Deleted: quick_score.py, scoring_formula.yaml, quick_score.md
- Pipeline: 7 stages

### Plans 01-08..10: Invest/Build Track Split (executed via GSD)
- 01-08: Triage + build signals (replicability, cis_gap_likelihood, stack_fit) + route field
- 01-09: lib/exa_client.py + 4 pipeline modules + 4 prompts
- 01-10: run_pipeline.py → 9-stage dual-track fork

### Bug Fixes (3x P1)
1. `llm.py` — returned raw string on JSON failure → now returns None
2. `deep_analysis.py` — read legacy web_research.md → now reads invest/build_research.md
3. `invest/build_research.py` — wrote str(None) as markdown → now writes failure message
4. `triage.py` — slug mismatch (file_path.stem vs make_slug) → 0 researched → fixed

### Pipeline Runs & Analysis
- Run 3 (01-07): 424→307→271→206 analyzed. 1 INVEST, 174 WATCH, 195 BUILD/PARTNER (inflated)
- Run 4 (01-08): build_candidate 78%→19%, route split: invest=145, build=26, both=33, skip=103
- Root causes identified: LLM training data hallucination in research, product evidence too loose

### Research (3 parallel agents)
- Landscape: Harmonic, Affinity, PitchBook. Our dual-track is unique. $3/run vs $24K/year.
- Code quality: 15 findings, 4x P1 (duplication, data flow, JSON garbage, semaphore)
- LLM optimization: incremental pipeline highest ROI, batching possible for triage

### Documentation Overhaul
- Roadmap: 7 phases → 4 phases (Phase 2+3 parallel, Phase 4 after both)
- REQUIREMENTS.md: consolidated to match 4-phase structure
- STATE.md: updated with all decisions and bug fixes
- CLAUDE.md: pipeline flow updated to 9-stage dual-track
- docs/IMPROVEMENT_PLAN.md: full analysis with prioritized recommendations

## Current Pipeline Architecture

```
parse → prefilter → triage ─┬─ invest (145) → invest_research → invest_gate → analysis
                             ├─ build (26)   → build_research  → build_gate  → analysis
                             ├─ both (33)    → both tracks
                             └─ skip (103)   → no research
```

Config: build track on, invest track off by default. Changeable in config/triage.yaml.

## Roadmap (4 phases)

| Phase | Status | Scope |
|-------|--------|-------|
| 1: MVP Pipeline | COMPLETE | 11 plans, 9-stage dual-track, web search |
| 2: Multi-Source + Delivery | Ready to plan | 10+ parsers + Telegram bot + cron |
| 3: Research Quality + Arch | Ready to plan (parallel w/2) | Refactor duplication, Exa, incremental, tests |
| 4: Production Polish | Blocked by 2+3 | Noise filtering, advanced scouting, docs |

## Pending Actions

1. Run full pipeline with web search to validate end-to-end
2. Plan Phase 2 or 3 (can be parallel)
3. Merge invest_*/build_* duplication (Phase 3 scope)
4. Tighten product evidence prompt (51%→target 20-30%)

## Files (3324 lines Python)

```
lib/          — llm.py, web_search.py, exa_client.py, scraper.py, utils.py, logger.py
pipeline/     — prefilter, triage, invest_research, build_research, invest_gate, build_gate,
                deep_analysis, digest_generator, deep_research (legacy), research_gate (legacy)
scouts/       — dealpad_parser.py
config/       — triage.yaml, scoring_weights.yaml, filters.yaml
prompts/      — triage, classify, invest_research, build_research, invest_gate, build_gate,
                deep_analysis, digest, research_gate (legacy)
run_pipeline.py — 9-stage orchestrator with --reset, --fresh, configurable tracks
```

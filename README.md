# Startup Scouting Pipeline

Automated startup scouting system for iFree -- a tech company launching investment activity and searching for ideas for its own products. Scans global deal flow, filters noise, researches via web search, and delivers weekly digests with actionable recommendations.

## Vision

The system monitors 15+ startup sources worldwide, detects opportunities before they become obvious, and delivers a 3-minute morning digest with:
- **Invest candidates** -- startups matching iFree's thesis ($30K-$300K, seed/early growth)
- **Build opportunities** -- hot niches with CIS market gaps that iFree can replicate
- **Trend reports** -- where capital is flowing, which categories are heating up

The key insight: **the same data stream powers two different lenses**. A YC-backed startup is both a potential investment AND a signal that its niche has no CIS analogue yet.

## How It Works

10-stage build-track funnel with deep research. Source-agnostic -- any parser feeds the same pipeline.

```
Sources (DealPad, GitHub, HN, PH, vc.ru...)
    ↓
[1]  Parse → 1_ideas/*.md (raw findings, Markdown + YAML frontmatter)
[2]  Pre-filter (LLM) → archive obvious rejects
[3]  Triage (8 binary questions) → route: invest / build / both / skip
    ↓                                    ↓
[4]  Invest research (web search)   [5] Build research (web search: CIS gap, OSS)
[6]  Invest gate (evidence check)   [7] Build gate (CIS gap OR replicable+demand)
                                    [7.5] Deep Research via Parallel AI (autonomous research, citations)
    ↓                                    ↓
[8]  Deep analysis (heavy LLM, BUILD-ONLY in Phase 2: kill signals + executive summary)
[9]  Digest (deterministic-first: byte-for-byte executive summaries + narrow LLM synthesis) → digests/weekly, monthly
```

> **Phase 2 temporary limitation:** Invest deep analysis is not supported in Phase 2 — it will be re-added in a future phase with a separate prompt. Setting `pipeline_tracks.invest=true` triggers a `SystemExit` at the deep_analysis step (honest-failure pattern: anchoring-bias risk if invest+build share an LLM context).

**Human-in-the-loop at transitions.** Automation collects and analyzes. Humans decide what to research deeper. The pause between Ideas and Research filters hype -- after a week, the real signal becomes visible.

## Current State (MVP)

Single source (DealPad Telegram export), build track active. 430 startups per batch → 18 build candidates → 11 pass gate → scored and analyzed with CIS adaptation recommendations.

```bash
# Quick start
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set OPENROUTER_API_KEY
python run_pipeline.py --html data/ChatExport_2026-04-13/messages.html --fresh
```

## Roadmap

### Phase 1: MVP Pipeline (DONE)
Single source (DealPad), dual-track architecture, web search research, config-driven track control, weekly digest.

### Phase 2: Deep Research + Pipeline Quality Upgrade (DONE, BUILD-ONLY)
- **Stage 7.5 Deep Research** via Parallel AI Task API — autonomous research with citations for gate-passed startups (`pipeline/deep_research_v2.py`)
- **Stage 8 Deep Analysis rewrite** — BUILD-only with kill signals (market_occupied, high_capital, far_from_competencies, long_time_to_revenue) + 7-field executive summary. Canonical verdict taxonomy: `build_verdict ∈ {BUILD, PARTNER, MONITOR, SKIP}` + separate `killed: bool` / `kill_reason: str`.
- **Stage 9 Digest rewrite** — deterministic-first: Python composes per-startup sections with byte-for-byte `executive_summary` insertion; LLM narrowly synthesizes `{key_findings, trends}`. No numeric score leakage.
- **Anti-anchoring context** — Parallel AI brief includes raw Stage 5 evidence as PRIMARY (URLs + snippets) and the LLM-synthesized summary as SECONDARY hint, framed as "validate or refute, NOT authoritative".
- **Honest invest guard** — `pipeline_tracks.invest=true` triggers `SystemExit` at deep_analysis (no silent mis-scoring).
- **Shared helper layer** — `lib/research_utils.py` with `_format_gate_signals` + `_format_raw_evidence`, consumed by both Stage 7.5 and Stage 8.

### Phase 3: Multi-Source + Delivery
- **10+ parsers** covering global and Russian sources (GitHub Trending, HN, ProductHunt, Reddit, vc.ru, Telegram channels, YC Companies, RSS feeds)
- **BaseScout pattern** -- each parser is a standalone file, failure of one doesn't block others
- **Cross-source deduplication** -- same startup from 3 sources = multi_source signal bonus
- **Telegram bot** -- morning digest delivery, `/top`, `/build`, `/status` commands
- **Cron automation** -- parsers 3x/day, digest every morning

### Phase 4: Research Quality + Architecture
- **core/ abstraction layer** -- idea_store, research_store, analysis_store replace direct file ops
- **GitHub API enrichment** -- stars, forks, contributors, commit activity for OSS assessment
- **Incremental processing** -- only new ideas since last run
- **Prompt versioning + cost tracking** per run
- **Fake traction detection** -- stars spike without forks/issues, stars:forks >50:1
- **Invest deep analysis** re-added as a separate prompt + LLM call (resolves Phase 2 temporary limitation)

### Phase 5: Production Polish
- **Human-in-the-loop review UI** -- pause between triage and research for manual candidate selection
- **Daily + weekly + monthly digest variants**
- **Build opportunities monthly report** (ranked, with CIS market sizing)
- **Founder tracker** -- monitor specific people's GitHub/LinkedIn activity
- **YC Lookalike search** -- find CIS-replicable patterns in YC batches

## Architecture

### Three Folders = Entire Database
```
1_ideas/     → raw findings from all parsers
2_research/  → enriched data per startup (web search + LLM synthesis)
3_analysis/  → scoring, conclusions, CIS adaptation recommendations
digests/     → cumulative weekly/monthly reports (never deleted by reset)
```
No databases, no servers. Markdown files under version control.

### Config-Driven Tracks (`config/triage.yaml`)
```yaml
pipeline_tracks:
  build: true        # CIS replication opportunities
  invest: false       # Investment candidates
  include_both: true  # Include dual-routed startups
```
Disabled tracks skip research, gate, and analysis stages entirely -- zero wasted API calls.

### Web Search Backends
| Backend | Cost | Quality | When |
|---------|------|---------|------|
| DDG (default) | Free | Good | Always tried first, retry 3x with backoff |
| Sonar (fallback) | ~$0.005/req | Good (AI-synthesized) | Auto when DDG returns nothing |
| Exa (alternative) | ~$0.007/req | Best (full page text) | `SEARCH_BACKEND=exa` |

### LLM Integration
OpenRouter API with three model tiers:
- **Light** (Gemini Flash) -- triage, pre-filter, research synthesis, extraction
- **Medium** (Gemini Flash/Pro) -- gate stages (build_gate, invest_gate, research_gate) where binary decision quality matters
- **Heavy** (Gemini Pro) -- deep analysis, executive summaries, scoring

Plus **Parallel AI Task API** (Stage 7.5) — autonomous deep research with citations (`PARALLEL_API_KEY`, ~$0.025/run on `core` processor). Called only for gate-passed build candidates.

### Key Design Decisions
- **Idempotent stages** -- every stage checks for existing output. Safe to re-run, resume after crash.
- **Prompts separated from code** -- all LLM prompts in `prompts/` folder, no hardcoded strings.
- **Final file contracts from day 1** -- SCHEMA.md defines YAML frontmatter for all file types. No throwaway formats.
- **Delay is a feature** -- the pause between Ideas and Research filters hype. Don't auto-promote.

## Build Mode Patterns

What the system looks for in build track:

1. **YC trends → CIS adaptation** -- YC invests in N startups in category X, no Russian analogue exists
2. **OSS with stars but no business** -- 10K+ stars, active dev, no company → white-label, managed hosting, enterprise version
3. **Hot product + iFree audience = cross-sell** -- B2B product gaining traction that iFree's clients could use
4. **Hot niche, no dominant CIS player** -- multiple small startups, growing market, no leader

## Investment Thesis

Focus: AI/ML, fintech, gamedev, developer tools, infrastructure, automation.
Geography: Russia + global. Check: $30K-$300K. Stage: seed / early growth.
Key filter: **strong founders** -- team matters more than idea.
Funnel: ~30 startups → 1-2 investments.

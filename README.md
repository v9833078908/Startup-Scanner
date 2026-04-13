# Startup Scouting Pipeline

Automated startup scouting system for iFree. Parses deal flow from Telegram channels, filters, triages, researches via web search, and produces weekly digests with build/invest recommendations.

## Two Operating Modes

- **Invest mode** -- find startups to invest in ($30K-$300K, seed/early growth)
- **Build mode** -- find hot niches and ideas for iFree's own products in CIS market

## Pipeline Architecture

9-stage dual-track funnel. Each stage is idempotent -- re-running skips already processed items.

```
[1/9] Parse DealPad HTML export         -> 1_ideas/*.md
[2/9] Pre-filter (LLM classification)   -> filtered/passed in frontmatter
[3/9] Triage (binary signals + route)   -> invest/build/both/skip route
[4/9] Invest research (web search)      -> 2_research/{slug}/invest_research.md
[5/9] Build research (web search)       -> 2_research/{slug}/build_research.md
[6/9] Invest gate (evidence check)      -> gate_invest.md + invest_analysis_ready
[7/9] Build gate (CIS gap + demand)     -> gate_build.md + build_analysis_ready
[8/9] Deep analysis (heavy LLM)         -> 3_analysis/{slug}_analysis.md
[9/9] Digest generation                 -> digests/{YYYY}-W{WW}_weekly.md
```

Tracks are controlled via `config/triage.yaml` -> `pipeline_tracks`. Disabled tracks skip stages 4-8 entirely.

## Quick Start

```bash
# 1. Create venv
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env: set OPENROUTER_API_KEY (required)

# 4. Run pipeline
python run_pipeline.py --html data/ChatExport_2026-04-13/messages.html

# Fresh run (clear old ideas, parse only new export)
python run_pipeline.py --html data/ChatExport_2026-04-13/messages.html --fresh

# Re-run on same data (restore archive, strip fields)
python run_pipeline.py --html data/ChatExport_2026-04-13/messages.html --reset
```

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for LLM calls |
| `OPENROUTER_MODEL_LIGHT` | Yes | Cheap/fast model for triage, research (e.g. `google/gemini-2.5-flash`) |
| `OPENROUTER_MODEL_HEAVY` | Yes | Strong model for deep analysis (e.g. `google/gemini-2.5-pro`) |
| `SEARCH_BACKEND` | No | `ddg` (default, free) or `exa` (needs `EXA_API_KEY`) |
| `EXA_API_KEY` | No | Only needed if `SEARCH_BACKEND=exa` |

### Pipeline Tracks (`config/triage.yaml`)

```yaml
pipeline_tracks:
  build: true           # Run build research/gate/analysis
  invest: false          # Run invest research/gate/analysis
  include_both: false    # Include "both"-routed startups in enabled tracks
```

### Search Backends

Three backends with automatic fallback:

| Backend | Cost | Quality | When |
|---------|------|---------|------|
| **DDG** (default) | Free | Good (snippets) | Always tried first |
| **Sonar** (fallback) | ~$0.005/req | Good (AI-synthesized) | Auto when DDG returns nothing |
| **Exa** (alternative) | ~$0.007/req | Best (full page text) | Manual via `SEARCH_BACKEND=exa` |

## Project Structure

```
StartupScanner/
  1_ideas/              Raw findings from parser (Markdown + YAML frontmatter)
  2_research/           Enriched data per startup (web search + LLM synthesis)
  3_analysis/           Deep analysis with scoring and recommendations
  digests/              Weekly/monthly digest reports (cumulative, never deleted)
  _archive/             Pre-filtered ideas moved here

  scouts/               Source parsers (DealPad, future: GitHub, HN, PH...)
  pipeline/             Pipeline stages (prefilter, triage, research, gate, analysis)
  lib/                  Shared libraries (LLM client, web search, scraper, utils)
  prompts/              LLM prompt templates (separate from code)
  config/               YAML configuration (triage rules, scoring weights)
  tests/                Smoke and integration tests

  run_pipeline.py       Main orchestrator
  THESIS.md             Investment thesis and focus areas
  SCHEMA.md             YAML frontmatter contracts for all file types
```

## Key Design Decisions

- **No database** -- Markdown files ARE the database. Everything under version control.
- **Human-in-the-loop** -- Automation collects and analyzes. Humans decide what to research deeper.
- **Idempotent stages** -- Each stage checks for existing output before processing. Safe to re-run.
- **Config-driven** -- Track selection, scoring weights, gate thresholds all in YAML.
- **Prompts separated from code** -- All LLM prompts in `prompts/` folder.

## Scoring

### Build Mode (8 criteria, 1-10 scale)
- **BUILD** (>=8): Strong opportunity, begin development
- **PARTNER** (6-7.9): Worth monitoring, potential partnership
- **MONITOR** (4-5.9): Interesting niche, watch for signals
- **SKIP** (<4): Not viable for CIS market

### Invest Mode (10 criteria, 1-10 scale)
- **INVEST** (>=8): Strong candidate, schedule meeting
- **WATCH** (6-7.9): Monitor for progress
- **PASS** (<6): Does not meet criteria

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Regenerate digest only (uses existing analysis)
python -c "import asyncio; from pipeline.digest_generator import run_digest; asyncio.run(run_digest())"
```

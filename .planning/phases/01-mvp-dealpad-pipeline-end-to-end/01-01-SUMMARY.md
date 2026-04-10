---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: "01"
subsystem: foundation
tags: [setup, config, lib, prompts, venv]
dependency_graph:
  requires: []
  provides:
    - python-venv-with-deps
    - config/filters.yaml
    - config/scoring_weights.yaml
    - lib/llm.py
    - lib/scraper.py
    - lib/utils.py
    - prompts/quick_score.md
    - prompts/deep_analysis.md
    - prompts/digest.md
    - THESIS.md
    - SCHEMA.md
  affects:
    - all subsequent plans (all pipeline steps import lib/ and load prompts/)
tech_stack:
  added:
    - openai>=1.0 (AsyncOpenAI pointed at OpenRouter base_url)
    - httpx>=0.27 (async HTTP for scraping)
    - beautifulsoup4>=4.12 + lxml>=5.0 (HTML parsing)
    - pyyaml>=6.0 (config loading)
    - python-dotenv>=1.0 (env var loading)
    - python-frontmatter>=1.1.0 (YAML frontmatter read/write)
    - dateparser>=1.2 (multilingual date parsing)
  patterns:
    - Async LLM client with Semaphore(5) concurrency control
    - 3-retry exponential backoff for LLM calls
    - json_object response_format with markdown code-fence stripping
    - Prompts as standalone .md files loaded at call time via load_prompt()
key_files:
  created:
    - requirements.txt
    - .env.example
    - lib/__init__.py
    - lib/llm.py
    - lib/scraper.py
    - lib/utils.py
    - scouts/__init__.py
    - pipeline/__init__.py
    - config/filters.yaml
    - config/scoring_weights.yaml
    - prompts/quick_score.md
    - prompts/deep_analysis.md
    - prompts/digest.md
    - THESIS.md
    - SCHEMA.md
  modified:
    - (none)
decisions:
  - "api_key fallback to 'not-set' string so AsyncOpenAI client initializes without a real key set — avoids import errors during development and testing"
  - "include_niches count is 29 (not 26 as stated in plan task description) — authoritative spec from docs/MVP_Plan.md has 29 entries, which is what was implemented"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-10"
  tasks_completed: 4
  files_created: 15
  files_modified: 0
---

# Phase 1 Plan 1: Project Foundation Summary

## One-liner

Python venv with 8 deps, 10-directory structure, async OpenRouter LLM client with semaphore+retry, website scraper, slug/date/round utilities, invest+build config files, and three complete LLM prompt files.

## What Was Built

### Task 1: Project setup
- Python venv at `.venv/` with all 8 dependencies installed cleanly
- `requirements.txt` with pinned minimum versions
- `.env.example` documenting all three required env vars (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL_LIGHT`, `OPENROUTER_MODEL_HEAVY`)
- 10 directories created: `config/`, `prompts/`, `scouts/`, `pipeline/`, `lib/`, `1_ideas/`, `2_research/`, `3_analysis/`, `_archive/`, `digests/`
- Python package stubs: `lib/__init__.py`, `scouts/__init__.py`, `pipeline/__init__.py`

### Task 1b: Reference documents
- `THESIS.md` — investment thesis with $30K–$300K check size, 6 focus sectors, invest/build modes, 4 build patterns, 3 deal flow streams
- `SCHEMA.md` — YAML frontmatter contracts for all pipeline file types (1_ideas, 2_research, 3_analysis, digests, _archive)

### Task 2: Config files
- `config/filters.yaml` — 29 include_niches, 14 exclude_niches, max_round_usd 500M, min_description_length 20
- `config/scoring_weights.yaml` — invest_mode (10 criteria, weights sum to 1.0), build_mode (8 criteria, weights sum to 1.0), red/green flags, thresholds per CLAUDE.md spec

### Task 3: Shared libraries and prompts
- `lib/llm.py` — async OpenRouter client (`AsyncOpenAI` with `base_url` override), `Semaphore(5)`, `call_llm` (3-retry backoff, json_object mode, code-fence stripping), `call_llm_batch` (gather with return_exceptions), `load_prompt`
- `lib/scraper.py` — `scrape_website` with httpx async client, lxml/BS4 parsing, tag decomposition (script/style/nav/header/footer/aside), max_chars truncation
- `lib/utils.py` — `make_slug` (NFKD normalize, ascii, hyphens, 50-char limit), `parse_round_usd` (K/M/B multipliers, $€£₽ symbols), `parse_date` (dateparser ru+en), `load_idea`/`save_idea` (python-frontmatter)
- `prompts/quick_score.md` — invest+build scoring prompt with 6 output keys: invest_score, build_score, category, one_liner, invest_rationale, build_rationale
- `prompts/deep_analysis.md` — full 10-criterion invest + 8-criterion build analysis with all criteria names, weights, rationale fields, verdicts, cis_adaptation, risks, next_steps, red/green flags
- `prompts/digest.md` — digest generation with Pipeline Summary, INVEST Candidates, WATCH List, BUILD Opportunities, Trends, All Scored table sections

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AsyncOpenAI raises OpenAIError when api_key is None**
- **Found during:** Task 3 verification
- **Issue:** `AsyncOpenAI` client raises `OpenAIError: The api_key client option must be set` at module import time when `OPENROUTER_API_KEY` env var is not present (during development/CI without a real key)
- **Fix:** Changed `api_key=os.getenv("OPENROUTER_API_KEY")` to `api_key=os.getenv("OPENROUTER_API_KEY") or "not-set"` — client initializes cleanly, actual API calls will fail at runtime if key is genuinely missing (appropriate behavior)
- **Files modified:** `lib/llm.py`
- **Commit:** 4fcb1ce

**2. [Rule 1 - Data] include_niches count is 29, not 26**
- **Found during:** Task 2 verification
- **Issue:** Plan task description stated "26 keywords" but docs/MVP_Plan.md (authoritative spec) lists 29 entries in the YAML
- **Fix:** Implemented all 29 entries from the spec — authoritative source wins over description text
- **Files modified:** `config/filters.yaml`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 14b903a | Project setup — venv, deps, directory structure, .env.example |
| Task 1b | dbf9bfe | THESIS.md and SCHEMA.md |
| Task 2 | 49318fa | Config files — filters.yaml and scoring_weights.yaml |
| Task 3 | 4fcb1ce | Shared libs and three prompt files |

## Self-Check: PASSED

All 12 key files confirmed present on disk. All 4 task commits confirmed in git history.

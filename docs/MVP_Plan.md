# Startup Scanner MVP — Implementation Plan

## Context

iFree (tech company) needs a working MVP for a startup scouting pipeline in 3 days (deadline: April 13, 2026). The system parses the DealPad Telegram channel export (~430 startup funding announcements), filters through configurable criteria, scores via LLM, does deep research on shortlisted startups, and produces a weekly digest MD report. Two tracks: **Invest** (invest in the startup) and **Build** (copy/adapt the idea for CIS market or iFree's product portfolio). Demo for shareholders on April 15.

## Pipeline Architecture

```
DealPad HTML (430 posts)
    │
    ▼
[1] PARSE ──────────► 1_ideas/*.md (structured MD files)
    │
    ▼
[2] PRE-FILTER ─────► filter by config/filters.yaml (niches, anti-spam, size)
    │                  ~430 → ~60-100 relevant
    ▼
[3] LLM QUICK SCORE ► OpenRouter light model scores each on invest+build potential
    │                  using only DealPad data (name, description, round size)
    │                  ~60-100 → shortlist ~15-30
    ▼
[4] DEEP RESEARCH ──► For each shortlisted startup:
    │                  - scrape website
    │                  - web search for additional data
    │                  - save to 2_research/{slug}/
    ▼
[5] LLM DEEP ANALYSIS ► OpenRouter heavy model: full invest+build scoring
    │                    per CLAUDE.md criteria, save to 3_analysis/
    ▼
[6] DIGEST ──────────► digests/{date}_weekly.md — final report
```

## Project Location

Create new git repo at `~/Projects/scouting-pipeline/` (the CLAUDE.md and specs are in Obsidian for reference; code lives separately).

## File Structure

```
scouting-pipeline/
├── .env                          # OPENROUTER_API_KEY, model names
├── .gitignore
├── requirements.txt
├── config/
│   ├── filters.yaml              # Configurable filtering criteria
│   └── scoring_weights.yaml      # Invest + Build scoring weights
├── prompts/
│   ├── quick_score.md            # Prompt for step 3 (light scoring)
│   ├── deep_analysis.md          # Prompt for step 5 (full analysis)
│   └── digest.md                 # Prompt for digest generation
├── scouts/
│   └── dealpad_parser.py         # Parse DealPad HTML export
├── pipeline/
│   ├── prefilter.py              # Apply filters.yaml to parsed ideas
│   ├── quick_score.py            # LLM quick scoring (batch)
│   ├── deep_research.py          # Website scraping + web search
│   ├── deep_analysis.py          # LLM full analysis on shortlisted
│   └── digest_generator.py       # Generate weekly digest MD
├── lib/
│   ├── llm.py                    # OpenRouter API wrapper (async)
│   ├── scraper.py                # Website content extractor
│   └── utils.py                  # Shared utilities (slug, date parsing, etc.)
├── run_pipeline.py               # Main orchestrator: runs all steps sequentially
├── 1_ideas/                      # Parsed DealPad entries (auto-generated)
├── 2_research/                   # Deep research per shortlisted startup
├── 3_analysis/                   # LLM analysis results
├── _archive/                     # Filtered out
└── digests/                      # Final reports
```

## Implementation Steps

### Step 1: Project Setup (~15 min)
- Create repo at `~/Projects/scouting-pipeline/`
- `git init`, `.gitignore`, `requirements.txt`
- Create `python3 -m venv .venv`
- Install: `httpx`, `beautifulsoup4`, `openai`, `pyyaml`, `python-dotenv`
- Create `.env` with `OPENROUTER_API_KEY`, model names
- Create directory structure

### Step 2: Config Files (~20 min)

**config/filters.yaml** — editable criteria:
```yaml
# Niches to INCLUDE (pass if startup matches any)
include_niches:
  - AI
  - ML
  - machine learning
  - fintech
  - finance
  - payments
  - gamedev
  - gaming
  - developer tools
  - devtools
  - infrastructure
  - automation
  - SaaS
  - B2B
  - marketplace
  - analytics
  - data
  - cybersecurity
  - security
  - cloud
  - API
  - platform
  - robotics
  - edtech
  - healthtech
  - legaltech
  - logistics
  - HR tech
  - proptech

# Niches to EXCLUDE (reject if matches)
exclude_niches:
  - real estate development
  - oil
  - gas
  - petrochemical
  - mining
  - agriculture
  - farming
  - construction
  - senior living
  - nursing home
  - assisted living
  - traditional retail
  - food & beverage
  - restaurant

# Round size filter (null = no filter)
min_round_usd: null        # no minimum
max_round_usd: 500000000   # skip $500M+ mega-rounds (not startup territory)

# Anti-spam: skip if description is too short
min_description_length: 20

# Date range (null = no filter)
date_from: null
date_to: null
```

**config/scoring_weights.yaml** — from CLAUDE.md:
```yaml
invest_mode:
  criteria:
    founder_strength: 0.20
    product: 0.15
    traction: 0.15
    market: 0.10
    business_model: 0.10
    technology: 0.10
    ifree_fit: 0.10
    momentum: 0.05
    fundraising_fit: 0.03
    gut_feeling: 0.02
  thresholds:
    invest: 8.0
    watch: 6.0
    pass: 0.0

build_mode:
  criteria:
    market_opportunity: 0.30
    ifree_fit: 0.25
    technical_feasibility: 0.15
    speed_to_market: 0.10
    revenue_potential: 0.10
    defensibility: 0.05
    trend_alignment: 0.03
    gut_feeling: 0.02
  thresholds:
    build: 8.0
    partner: 6.0
    monitor: 4.0
    skip: 0.0

ifree_focus:
  sectors:
    - AI/ML
    - fintech
    - gamedev
    - developer tools
    - infrastructure
    - automation
  geography: "Russia + Global"
  check_size: "$30K-$300K"
  stage: "seed / early growth"
  key_filter: "strong founders — team matters more than idea"
```

### Step 3: DealPad Parser (`scouts/dealpad_parser.py`) (~30 min)

Parses the HTML export using BeautifulSoup:
- Select all `div.message.default.clearfix` elements
- Skip promotional messages (containing "обзоры" or "fastfounder")
- For each message extract:
  - `name`: first `<a>` tag text content
  - `url`: first `<a>` href
  - `round_raw`: parse "Раунд: $XXX, DATE" line
  - `round_usd`: normalize to USD number ($115K → 115000, $4B → 4000000000)
  - `round_date`: parse Russian date string
  - `description`: text after second `<br>`
  - `message_id`: from element id attribute
  - `post_date`: from `.date.details` title attribute
- Save each as `1_ideas/{YYYY-MM-DD}_{slug}.md` using template:

```markdown
---
name: {name}
url: {url}
round_usd: {round_usd}
round_raw: {round_raw}
round_date: {round_date}
source: dealpad
source_id: {message_id}
parsed_at: {now}
---

# {name}

**URL:** {url}
**Round:** {round_raw}
**Description:** {description}
```

### Step 4: Pre-filter (`pipeline/prefilter.py`) (~20 min)

Reads all MD files from `1_ideas/`, applies `config/filters.yaml`:
1. Parse YAML frontmatter from each file
2. Apply niche filter: check if description matches any `include_niches` keyword (case-insensitive). If `exclude_niches` match — reject.
3. Apply round size filter
4. Apply description length filter
5. Move rejected to `_archive/` with reason in frontmatter
6. Output: list of passing startups for next step

### Step 5: LLM Quick Score (`pipeline/quick_score.py`) (~40 min)

For each pre-filtered startup:
- Send name + description + round info to OpenRouter (light model)
- Prompt asks for JSON response with:
  - `invest_score` (1-10): how investable is this startup
  - `build_score` (1-10): how copyable/adaptable is the idea for CIS
  - `category`: startup's primary niche
  - `one_liner`: 1-sentence summary in Russian
  - `invest_rationale`: why invest / why not (1 sentence)
  - `build_rationale`: why build / why not (1 sentence)
- Append scores to the idea's MD frontmatter
- Produce shortlist: startups with invest_score >= 6 OR build_score >= 6
- Use async/await with concurrency limit (5 parallel requests)

### Step 6: Deep Research (`pipeline/deep_research.py`) (~40 min)

For each shortlisted startup:
- Create `2_research/{slug}/` directory
- **Scrape website** (`lib/scraper.py`): fetch main page, extract text content with BS4, save as `website.md`
- **Web search** (`lib/llm.py`): use OpenRouter to summarize what the company does, its founders, traction, competitive landscape — save as `web_research.md`
- Save combined data in the research folder

### Step 7: Deep Analysis (`pipeline/deep_analysis.py`) (~40 min)

For each researched startup:
- Load idea data + research data
- Send to OpenRouter (heavy model) with full scoring prompt
- Prompt includes investment thesis from scoring_weights.yaml
- Returns structured JSON with:
  - Full invest scoring (10 criteria with individual scores)
  - Full build scoring (8 criteria with individual scores)
  - Weighted total scores
  - Verdict: INVEST/WATCH/PASS + BUILD/PARTNER/MONITOR/SKIP
  - CIS adaptation potential (what exactly to adapt and how)
  - Risks and opportunities
  - Recommended next steps
- Save as `3_analysis/{slug}_analysis.md`

### Step 8: Digest Generator (`pipeline/digest_generator.py`) (~30 min)

Reads all analysis files, generates a single weekly digest MD:

```markdown
# Startup Scouting Digest — Week of {date}

## Pipeline Summary
- **Parsed:** {total} startups from DealPad
- **After pre-filter:** {filtered} relevant
- **Quick-scored:** {scored} with LLM
- **Shortlisted:** {shortlisted} for deep research
- **Final recommendations:** {final}

## INVEST Candidates (score >= 8)
{for each: name, score, round, what they do, why invest, key risk}

## WATCH List (score 6-7.9)
{table: name, score, category, one-liner, revisit date}

## BUILD Opportunities (build_score >= 6)
{for each: name, build_score, what to build, CIS adaptation, iFree fit, resources needed}

## Trends This Week
{top categories by count, notable patterns}

## All Scored Startups
{full table: name, invest_score, build_score, category, round, verdict}
```

### Step 9: Orchestrator (`run_pipeline.py`) (~15 min)

Sequential runner:
```python
python run_pipeline.py --html path/to/messages.html
```
Runs steps 1-6 in order, prints progress. Each step is idempotent — can re-run safely.

## Key Technical Decisions

1. **OpenRouter via openai SDK** — point `base_url` at `https://openrouter.ai/api/v1`, use `OPENROUTER_API_KEY`
2. **Async with httpx** — for parallel LLM calls and website scraping
3. **YAML frontmatter in MD files** — machine-readable metadata + human-readable content
4. **All prompts in `prompts/` folder** — per CLAUDE.md rules, never in code
5. **Config-driven filtering** — `filters.yaml` is the single source of truth for what passes/fails

## Verification

1. Run `python run_pipeline.py --html "path/to/messages.html"` 
2. Check `1_ideas/` has ~430 MD files
3. Check `_archive/` has rejected startups with reasons
4. Check shortlist has ~15-30 startups
5. Check `2_research/` has folders with website + research data
6. Check `3_analysis/` has scoring files with invest + build verdicts
7. Check `digests/` has the weekly report
8. Review digest manually — does the shortlist make sense?

## Estimated Time

| Step | Time |
|------|------|
| 1. Setup | 15 min |
| 2. Config files | 20 min |
| 3. DealPad parser | 30 min |
| 4. Pre-filter | 20 min |
| 5. Quick score | 40 min |
| 6. Deep research | 40 min |
| 7. Deep analysis | 40 min |
| 8. Digest generator | 30 min |
| 9. Orchestrator | 15 min |
| **Total coding** | **~4 hours** |

API runtime for ~60 startups through quick score + ~20 through deep analysis: ~10-15 min depending on rate limits.

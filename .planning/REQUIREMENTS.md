# Requirements — Startup Scouting Pipeline

## Phase 1: MVP DealPad Pipeline (COMPLETE)

### R1: Project Setup
- Python project with venv, .env, .gitignore
- Directory structure: 1_ideas/, 2_research/, 3_analysis/, _archive/, digests/, scouts/, pipeline/, lib/, prompts/, config/

### R2: Config Files
- config/triage.yaml — invest/build signals, gate thresholds, pipeline track config, route rules
- config/scoring_weights.yaml — invest mode (10 criteria) + build mode (8 criteria) weights and thresholds

### R3: DealPad HTML Parser
- Parse DealPad Telegram HTML export, extract name/url/round/description
- Save as 1_ideas/{YYYY-MM-DD}_{slug}.md with YAML frontmatter

### R4: Pre-filter (LLM Classification)
- LLM classifies: is_tech, sector, sector_match, product_type, b2b_b2c
- Hard reject: is_tech=false OR sector_match=no → archive
- Graceful failure: review_needed=true with safe fallback

### R5: Triage (Binary Evidence + Route)
- LLM answers 8 binary questions: 5 invest (product_evidence, founder_signal, barriers, one_liner, category) + 3 build (replicability, cis_gap_likelihood, stack_fit)
- Mechanical: invest_priority (high/medium/low from signal count), build_candidate (tighter: replicability + stack_fit)
- Route computation: invest/build/both/skip

### R6: Dual-Track Research (Web Search)
- Invest research: web search for founders, traction, funding via DDG/Exa
- Build research: web search for CIS competitors, OSS alternatives, market gaps
- Research files: 2_research/{slug}/invest_research.md, build_research.md

### R7: Dual-Track Gates
- Invest gate: 2/3 evidence threshold (team, traction, competitive)
- Build gate: CIS gap confirmed OR (replicable + market demand)
- Gate files: 2_research/{slug}/gate_invest.md, gate_build.md

### R8: Deep Analysis + Digest
- Heavy model scoring: invest (10 criteria) + build (8 criteria), weighted
- Configurable per track: build default on, invest default off, invest_top_n=20
- Weekly digest with pipeline summary + candidates + trends

## Phase 2: Multi-Source + Delivery

### R9: BaseScout Framework + Core Data Layer
- core/idea_store.py — save/load/archive/list/exists for ideas
- core/dedup.py — normalize_name, extract_domain, is_duplicate (domain OR Jaro-Winkler >0.85)
- BaseScout class: fetch_url, save_idea, already_exists, abstract run()

### R10: GitHub Trending + HN Parsers
- GitHub Trending: daily+weekly, stars_today >= 50, no tutorials/forks
- HN: Firebase API, Show HN / Launch HN, score > 50

### R11: RSS-Based Parsers
- RSS feeds (TechCrunch, Crunchbase News, Sifted) via feedparser
- vc.ru: RSS with Russian startup keywords
- Habr: RSS hubs startup + open_source

### R12: Betalist Parser
- Scrape betalist.com for latest beta launches

### R13: Product Hunt + Reddit
- Product Hunt: GraphQL API with auth, upvotes > 50
- Reddit: OAuth2, 4 subreddits, score > 20

### R14: Telegram + Russian Sources
- Telethon, 5+ channels, keyword filtering, URL extraction

### R15: YC + Indie Hackers
- YC Companies via yc-oss/api
- Indie Hackers: revenue milestones and launches

### R22: Telegram Bot (Delivery)
- core/digest_service.py — digest as data structure
- adapters/telegram_bot.py — /digest, /top, /build, /status
- Auto-alert on invest_score > 8

### R24: Cron & Orchestration
- Parsers 3x/day, daily digest every morning, weekly report Mondays
- status.py: pipeline state overview

## Phase 3: Research Quality + Architecture

### R16: GitHub & Website Enrichment
- core/research_store.py — research folder management
- enrich_github.py: stars, forks, issues, contributors, commits/30d
- enrich_website.py: main page + /about + /pricing + /team

### R17: Research Workflow
- enrich_mentions.py: HN Algolia + Reddit search
- Incremental processing: track processed IDs, skip already-triaged

### R18: Architecture Cleanup
- Merge invest_*/build_* into parameterized track modules
- Extract _coerce_bool(), format_search_results() to lib/utils.py
- Remove legacy dead code (deep_research.py, research_gate.py)
- Split config/triage.yaml into triage, gates, pipeline configs
- Unit tests for pure functions (compute_route, compute_build_candidate, etc.)

### R19: Prompt & Cost Management
- Prompt versioning in frontmatter
- Cost tracking per pipeline run
- Prompt compression (900 → 630 tokens triage prompt)

## Phase 4: Production Polish

### R20: Daily & Weekly Digests
- Daily: hot finds, new ideas 24h, pipeline movement
- Weekly: executive summary, INVEST cards, WATCH list, trends
- Monthly: top niches, open-source gems, macro signals

### R21: Build Reports
- Build opportunities: top-5 ranked, detailed breakdown
- Trend report: niche tracking over time

### R25: Advanced Scouting
- YC Lookalike: find similar non-YC repos, >100 stars
- Founder Tracker: config/tracked_founders.yaml, GitHub activity
- Chrome Extensions: monitor developer/productivity categories

### R26: Noise Filtering
- Fake traction: stars spike without forks, stars:forks >50:1
- Amateur startup auto-skip: >3 red flags

### R27: Documentation & Demo
- README: quickstart, parser docs, cron setup, FAQ
- Demo script: fake startup through full pipeline

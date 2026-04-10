# Requirements — Startup Scouting Pipeline

## Phase 1: MVP DealPad Pipeline

### R1: Project Setup
- Python project with venv, .env, .gitignore
- Directory structure: 1_ideas/, 2_research/, 3_analysis/, _archive/, digests/, scouts/, pipeline/, lib/, prompts/, config/
- Dependencies: httpx, beautifulsoup4, openai, pyyaml, python-dotenv

### R2: Config Files
- config/filters.yaml — include/exclude niches, round size limits, description length, date range
- config/scoring_weights.yaml — invest mode (10 criteria) + build mode (8 criteria) weights and thresholds

### R3: DealPad HTML Parser
- Parse div.message.default.clearfix elements from DealPad HTML export
- Extract: name, url, round_raw, round_usd (normalize $115K→115000), round_date, description, message_id, post_date
- Skip promotional messages (containing "обзоры" or "fastfounder")
- Save as 1_ideas/{YYYY-MM-DD}_{slug}.md with YAML frontmatter

### R4: Pre-filter
- Read all 1_ideas/ MD files, apply filters.yaml
- Niche filter: include_niches keyword match (case-insensitive), exclude_niches rejection
- Round size filter, description length filter
- Move rejected to _archive/ with reason in frontmatter

### R5: LLM Quick Score
- Send name + description + round to OpenRouter (light model)
- Return JSON: invest_score, build_score, category, one_liner, invest_rationale, build_rationale
- Append scores to idea frontmatter
- Shortlist: invest_score >= 6 OR build_score >= 6
- Async with concurrency limit (5 parallel)

### R6: Deep Research
- For each shortlisted startup: create 2_research/{slug}/
- Scrape website main page, extract text with BS4
- Web search via OpenRouter for company info, founders, traction, competitors

### R7: Deep Analysis
- Load idea + research data, send to OpenRouter (heavy model)
- Full invest scoring (10 criteria) + build scoring (8 criteria)
- Return: weighted scores, verdicts, CIS adaptation potential, risks, next steps
- Save as 3_analysis/{slug}_analysis.md

### R8: Digest & Orchestrator
- Generate weekly digest MD with: pipeline summary, INVEST candidates, WATCH list, BUILD opportunities, trends, all scored startups table
- run_pipeline.py --html path/to/messages.html runs steps 1-6 sequentially
- Each step is idempotent

## Phase 2: Scout Framework + Simple Parsers

### R9: BaseScout Framework
- BaseScout class: fetch_url (retry 3, timeout 15s, random UA), save_idea (MD template), already_exists (dedup), abstract run()
- Jaro-Winkler dedup: normalize_name (strip Inc/Ltd/AI/Labs/.io/.ai/.dev/.com), extract_domain, is_duplicate (domain OR fuzzy >0.85)
- Built-in Jaro-Winkler implementation (no external library)

### R10: GitHub Trending + HN Parsers
- GitHub Trending: parse daily+weekly, filter (no tutorials/awesome-lists, stars_today >= 50, has description >20 chars, not fork)
- Hacker News: Firebase API, Show HN / Launch HN filter, score > 50, cache seen IDs, max 100 items/run

### R11: RSS-Based Parsers
- RSS feeds: feedparser, config-driven feeds list with keywords
- vc.ru: RSS with Russian startup keywords
- Habr: RSS hubs startup + open_source, rating filter

### R12: Betalist Parser
- Scrape betalist.com for latest beta launches

## Phase 3: Auth-Based & Complex Parsers

### R13: Product Hunt + Reddit
- Product Hunt: GraphQL API with auth token, top-20 products, upvotes > 50
- Reddit: OAuth2 setup, 4 subreddits, score > 20, external URL + keyword match, rate limit 1 req/2s

### R14: Telegram + Russian Sources
- Telegram: Telethon, config/telegram_channels.yaml (5+ channels), keyword filtering, URL extraction, state tracking
- Auth: interactive Telethon authorization on first run

### R15: YC + Indie Hackers + Founder Tracker
- YC Companies: yc-oss/api or scraping, latest batch, all pass filter (pre-filtered)
- Indie Hackers: scraping for revenue milestones and launches
- Founder Tracker: config/tracked_founders.yaml, GitHub API for new repos (30 days)

## Phase 4: Research Enrichment

### R16: GitHub & Website Enrichment
- enrich_github.py: stars, forks, issues, watchers, contributors, commits/30d, languages, topics, stars_per_day
- enrich_website.py: main page + /about + /pricing + /features + /team, BS4 text extraction

### R17: Mentions & Research Workflow
- enrich_mentions.py: HN Algolia API + Reddit search API
- move_to_research.py: create 2_research/{slug}/, copy idea, create profile.md, run all enrichments
- --all-older-than N flag for batch processing

## Phase 5: Full Scoring & Reports

### R18: Config-Driven Scoring Module
- Read weights from scoring_weights.yaml
- Invest: 10 criteria + red flags (no_linkedin=-2, no_product=-2, fake_stars=-3) + green flags (yc=+2, prev_exit=+2, warm_intro=+2, multi_source=+1)
- Build: 8 criteria, thresholds BUILD/PARTNER/MONITOR/SKIP

### R19: Enhanced Analysis Agent
- OpenRouter heavy model with full prompts from prompts/ folder
- Invest mode: 10 criteria scoring + за/против + recommendation
- Build mode: 8 criteria + what to build + iFree advantages + risks
- --mode invest|build|both flag

### R20: Daily & Weekly Digests
- Daily: hot finds (score >= 8), new ideas 24h, pipeline movement, build opportunities, source efficiency
- Weekly: executive summary, INVEST cards (full), WATCH list, build opportunities (detailed), trends, pipeline status

### R21: Trend & Build Reports
- Monthly trends: top-10 niches, open-source gems, founders to watch, macro signals
- Build opportunities: top-5 ranked by build_score, detailed breakdown per idea

## Phase 6: Delivery & Automation

### R22: Telegram Bot
- Commands: /status, /new, /top, /build, /digest
- Auto-alerts on invest_score > 8
- Config: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env

### R23: Email Delivery
- Resend API integration
- Send MD digest as formatted email
- Config: RESEND_API_KEY, recipient email in .env

### R24: Cron & Orchestration
- run_all_scouts.sh: sequential run of all parsers, continue on error
- status.py: pipeline state overview
- full_pipeline.py: complete interactive cycle
- Crontab instructions in README

## Phase 7: Advanced Features

### R25: YC Lookalike + Chrome Extensions
- YC Lookalike: generate search queries from YC descriptions, find similar non-YC repos, >100 stars, recent commits
- Chrome Extensions: monitor Chrome Web Store productivity/developer categories

### R26: Noise Filtering
- Fake traction: stars spike without forks/issues/commits, stars:forks >50:1, no mentions outside GitHub
- "Amateur startup" auto-skip: >3 red flags (no LinkedIn/GitHub, no product, free hosting, solo, single mention, generic description)

### R27: Documentation & Demo
- README: quickstart, parser descriptions, add new source guide, cron setup, invest vs build workflow, FAQ
- Demo script: fake startup through full pipeline
- convert-to-MD utility: PDF, DOCX, XLSX, PPTX, HTML → Markdown

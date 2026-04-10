# Roadmap — Startup Scouting Pipeline

## Milestone 1: Scouting Pipeline v1.0

### Phase 1: MVP — DealPad Pipeline End-to-End
- **Goal:** Working pipeline: DealPad HTML export → weekly digest report for shareholder demo (April 15)
- **Deadline:** April 13, 2026
- **Requirements:** R1, R2, R3, R4, R5, R6, R7, R8
- **Success Criteria:**
  - [ ] `run_pipeline.py --html messages.html` runs end-to-end without errors
  - [ ] `1_ideas/` contains ~430 parsed MD files from DealPad
  - [ ] Pre-filter reduces to ~60-100 relevant startups
  - [ ] Quick score shortlists ~15-30 startups (invest_score >= 6 OR build_score >= 6)
  - [ ] `2_research/` has folders with website + research data for shortlisted
  - [ ] `3_analysis/` has scoring files with invest + build verdicts
  - [ ] `digests/` contains a complete weekly report with all sections
  - [ ] Digest makes sense on manual review
- **Plans:** 0/0

### Phase 2: Scout Framework + Simple Parsers
- **Goal:** Reusable scout architecture + 6 new parsers for broad source coverage via simple APIs
- **Requirements:** R9, R10, R11, R12
- **Depends on:** Phase 1
- **Success Criteria:**
  - [ ] BaseScout class with fetch_url, save_idea, already_exists methods
  - [ ] Jaro-Winkler dedup (>0.85 threshold) catches cross-source duplicates
  - [ ] DealPad parser refactored to inherit BaseScout
  - [ ] GitHub Trending parser produces ideas from daily+weekly trending
  - [ ] Hacker News parser captures Show HN / Launch HN with score > 50
  - [ ] RSS parser processes TechCrunch, Crunchbase, Sifted feeds
  - [ ] vc.ru parser captures startup articles from RSS
  - [ ] Habr parser captures startup + open-source articles
  - [ ] Betalist parser captures beta launches
  - [ ] All parsers respect entry thresholds from CLAUDE.md
  - [ ] Multi-source startups detected and flagged (bonus signal)
- **Plans:** 0/0

### Phase 3: Auth-Based & Complex Parsers
- **Goal:** Complete 15-source coverage including auth-required and complex parsers
- **Requirements:** R9, R13, R14, R15
- **Depends on:** Phase 2
- **Success Criteria:**
  - [ ] Product Hunt parser works via GraphQL API with auth
  - [ ] Reddit parser works via OAuth2 for 4 subreddits (SaaS, startups, MachineLearning, selfhosted)
  - [ ] Telegram parser reads last 30 messages from 5 configured channels via Telethon
  - [ ] YC Companies parser fetches latest batch via yc-oss/api
  - [ ] Indie Hackers parser captures revenue milestones and launches
  - [ ] Founder Tracker monitors configured founders' GitHub activity
  - [ ] All 15 parsers run successfully via single script
  - [ ] Total idea coverage: 50-100+ ideas per full run across all sources
- **Plans:** 0/0

### Phase 4: Research Enrichment Pipeline
- **Goal:** Automated structured data collection for shortlisted startups
- **Requirements:** R16, R17
- **Depends on:** Phase 2
- **Success Criteria:**
  - [ ] enrich_github.py collects: stars, forks, issues, contributors, commits/30d, stars_per_day
  - [ ] enrich_website.py extracts text from main page, /about, /pricing, /team
  - [ ] enrich_mentions.py finds mentions on HN (Algolia API) and Reddit
  - [ ] move_to_research.py creates structured folder in 2_research/ and runs all enrichments
  - [ ] `--all-older-than 7` flag moves all ideas older than N days
  - [ ] Research folders contain: profile.md, github_metrics.md, website_content.md, social_mentions.md
- **Plans:** 0/0

### Phase 5: Full Scoring & Report Suite
- **Goal:** Complete analysis system with all 4 report types from Vision
- **Requirements:** R18, R19, R20, R21
- **Depends on:** Phase 4
- **Success Criteria:**
  - [ ] Scoring module reads weights from config/scoring_weights.yaml
  - [ ] Invest scoring: 10 criteria + red/green flags, returns INVEST/WATCH/PASS
  - [ ] Build scoring: 8 criteria, returns BUILD/PARTNER/MONITOR/SKIP
  - [ ] Daily digest: hot finds, new ideas, pipeline movement, build opportunities, source stats
  - [ ] Weekly report: executive summary, INVEST cards, WATCH list, build opportunities, trends
  - [ ] Monthly trend report: top niches, open-source gems, founders to watch, macro signals
  - [ ] Build opportunities report: ranked ideas with iFree fit analysis
- **Plans:** 0/0

### Phase 6: Delivery & Automation
- **Goal:** System runs autonomously and delivers results to team
- **Requirements:** R22, R23, R24
- **Depends on:** Phase 5
- **Success Criteria:**
  - [ ] Telegram bot responds to /status, /new, /top, /build, /digest
  - [ ] Auto-alert when invest_score > 8 detected
  - [ ] Email delivery via Resend API works
  - [ ] Cron: parsers 3x/day, daily digest every morning, weekly report on Mondays
  - [ ] status.py shows pipeline state (ideas/research/analysis/archive counts)
  - [ ] full_pipeline.py runs complete cycle with interactive research selection
- **Plans:** 0/0

### Phase 7: Advanced Features & Polish
- **Goal:** Special parsers, noise filtering, and production readiness
- **Requirements:** R25, R26, R27
- **Depends on:** Phase 3
- **Success Criteria:**
  - [ ] YC Lookalike Search finds repos similar to current YC batch companies
  - [ ] Chrome Extensions parser monitors productivity/developer categories
  - [ ] convert-to-MD utility handles PDF, DOCX, XLSX, PPTX, HTML
  - [ ] Fake traction detection: stars spike without forks/issues, stars:forks >50:1
  - [ ] "Amateur startup" auto-skip when >3 red flags present
  - [ ] Demo script creates fake startup through full pipeline
  - [ ] README with quickstart, parser docs, cron setup, FAQ
- **Plans:** 0/0

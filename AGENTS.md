# Startup Scouting Pipeline — AGENTS.md

## Project Overview

Startup scouting system for iFree — a tech company (not a fund) launching investment activity and searching for ideas for its own products. Two operating modes from the same data stream:

- **Invest mode** — find startups to invest in ($30K–$300K, seed/early growth)
- **Build mode** — find hot niches, open-source projects, and ideas for iFree's own products

## Architecture Principles

### Three Folders = Entire Architecture
```
1_ideas/     → raw findings from all parsers (Markdown files)
2_research/  → enriched data per startup (folder with multiple .md files)
3_analysis/  → scoring, conclusions, recommendations (Markdown files)
```
No databases, no servers, no deployments. File system + scripts + OpenRouter API. Everything in Markdown, everything under version control.

### One File = One Module
Each scout/parser is a standalone file inheriting from `BaseScout`. One Codex session = one working script. Scripts are independent — failure of one does not block others.

### Human-in-the-Loop at Transitions
Automation collects and analyzes. Humans make decisions. Especially: moving from Ideas to Research is a deliberate choice, not automatic.

### Delay Is a Feature
The pause between Ideas and Research filters hype. After a week, the real signal becomes visible. Don't auto-promote ideas.

## Core Rules

1. **All parsers at once, not in phases.** 15 parsers in 2 days. Breadth of coverage from day one is fundamental. 15 simple parsers > 3 perfect ones.

2. **Digest is the main artifact.** The system's value is not in parsing — it's in the morning Telegram/email digest with ready-made recommendations and action items.

3. **4 days, not 4 weeks.** This is a sprint, not a roadmap. Every feature should be deliverable within a single session.

4. **Founder > Idea in invest mode. Market > Technology in build mode.** Two different focuses, two scoring systems. Never conflate them.

5. **Warm intros are the best channel.** The system supplements, not replaces, personal contacts. A startup from a trusted person goes straight to Ideas with a bonus.

## Coding Standards

### Python
- Always use venv
- Prefer `async/await` over callbacks for API calls
- Use `httpx` for HTTP, `beautifulsoup4` for scraping, `feedparser` for RSS, `telethon` for Telegram
- All prompts go in a separate folder — never hardcode prompts in business logic
- Config files in YAML (`config/`), secrets in `.env`

### LLM Integration
- Use **OpenRouter API** (`https://openrouter.ai/api/v1`) for all LLM calls — OpenAI-compatible interface
- Model names are set in `.env`, never hardcoded. Different models for different complexity:
  - `OPENROUTER_MODEL_LIGHT` — cheap/fast model for simple tasks (extraction, summarization, classification)
  - `OPENROUTER_MODEL_HEAVY` — stronger model for complex analysis (scoring, invest/build assessments, trend reports)
- API key: `OPENROUTER_API_KEY` in `.env`
- Use `openai` Python SDK pointed at OpenRouter base URL, or raw `httpx` calls

### File Naming
- Ideas: `{YYYY-MM-DD}_{slug}.md` — slug is lowercase, hyphens, no special chars
- Digests: `{YYYY-MM-DD}_daily.md`, `{YYYY}-W{WW}_weekly.md`, `{YYYY-MM}_trends.md`

### Scout Pattern
Every parser inherits `BaseScout` and implements `run()`. Uses:
- `fetch_url(url)` — HTTP GET with retry (3 attempts), 15s timeout, random user-agent
- `save_idea(data)` — creates MD file from template in `1_ideas/`
- `already_exists(url, name)` — dedup via domain match + Jaro-Winkler fuzzy name match (>0.85)

### Deduplication
- Exact domain match OR fuzzy name similarity >0.85
- `normalize_name()` strips Inc/Ltd/AI/Labs/.io/.ai/.dev/.com
- Built-in Jaro-Winkler — no external library for this

### Noise Filtering
Apply entry thresholds per source (GitHub: <50 stars/week skip; HN: <50 points skip; PH: <100 upvotes skip; Reddit: <20 upvotes skip). Auto-skip "amateur startups" when >3 red flags present (no LinkedIn/GitHub, no working product, free hosting, solo with 0 contributors, single mention in 30 days, generic description).

### Fake Traction Detection
- Stars spike without forks/issues/commits → flag, don't boost score
- Stars:forks ratio >50:1 → suspicious
- No mentions outside GitHub → likely fake

## Scoring

### Invest Mode (10 criteria, 1–10 scale)
Weights: founder_strength=20%, product=15%, traction=15%, market=10%, business_model=10%, technology=10%, ifree_fit=10%, momentum=5%, fundraising_fit=3%, gut_feeling=2%.
- INVEST: >=8 | WATCH: 6–7.9 | PASS: <6
- Red flags: no_linkedin=-2, no_product=-2, fake_stars=-3
- Green flags: yc=+2, prev_exit=+2, warm_intro=+2, multi_source=+1

### Build Mode (8 criteria, 1–10 scale)
Weights: market_opportunity=30%, ifree_fit=25%, technical_feasibility=15%, speed_to_market=10%, revenue_potential=10%, defensibility=5%, trend_alignment=3%, gut_feeling=2%.
- BUILD: >=8 | PARTNER: 6–7.9 | MONITOR: 4–5.9 | SKIP: <4

Scoring weights are in `config/scoring_weights.yaml` — changeable without touching code.

## Investment Thesis

Focus areas: AI/ML, fintech, gamedev, developer tools, infrastructure, automation.
Geography: Russia + global.
Check size: $30K–$300K per deal.
Stage: seed / early growth.
Funnel: ~30 startups → 1–2 investments.
Key filter: **strong founders** — team matters more than idea.

### Build Mode Patterns
1. **YC trends → Russian adaptation** — YC invests in N startups in category X, no Russian analogue exists
2. **Open-source with stars but no business** — 10K+ stars, active dev, no company/revenue → white-label, managed hosting, enterprise version
3. **Hot product + iFree audience = cross-sell** — new B2B product gaining traction that iFree's clients could use
4. **Hot niche, no dominant player** — multiple small startups, growing market, no leader yet

## Data Sources (15 parsers)

### Global
GitHub Trending, GitHub Repo Metrics, Hacker News, Product Hunt, Reddit (r/SaaS, r/startups, r/MachineLearning, r/selfhosted), YC Companies, Indie Hackers, RSS feeds (TechCrunch, Crunchbase News, Sifted), Betalist

### Russian
Telegram channels (5+), vc.ru, Habr

### Special
Founder Tracker (monitor specific people), YC Lookalike Search, Chrome Extensions

## Pipeline Flow

```
Parsers → 1_ideas/ → (human decides) → 2_research/ → (enrichment) → 3_analysis/ → digests/
```

Research enrichment: GitHub metrics, website content, social mentions.
Analysis: OpenRouter API for both invest and build mode assessments. Model is set via env vars — different models for different task complexity (cheap model for simple extraction, stronger model for analysis/scoring).

## Output Artifacts

| Artifact | Frequency | Purpose |
|----------|-----------|---------|
| Daily Digest | Every morning | 3-min overview: hot finds, new ideas, pipeline movement |
| Weekly Report | Every Monday | Strategic review: INVEST candidates, WATCH list, trends |
| Trend Report | Monthly | Top niches, open-source gems, macro signals |
| Build Opportunities | Monthly | Ranked ideas for iFree's own products |

## Don'ts

- Don't over-engineer. No frameworks, no ORMs, no microservices. Scripts + files + git.
- Don't auto-promote ideas to research. That's a human decision.
- Don't trust stars without other signals. Always cross-reference.
- Don't create a database. Markdown files ARE the database.
- Don't build delivery (Telegram bot, email) before the pipeline itself works end-to-end.
- Don't optimize a single parser at the expense of coverage. Breadth first.
- Don't skip deduplication. The same startup appears on multiple sources — that's a signal (multi_source bonus), not a bug, but the file should exist once.

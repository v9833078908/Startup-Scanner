# File Schemas — Scouting Pipeline

## 1_ideas/{YYYY-MM-DD}_{slug}.md

YAML frontmatter contract:
```yaml
name: string           # Startup name
url: string            # Website URL
round_usd: int|null    # Normalized round in USD
round_raw: string      # Original round string (e.g., "$115K")
round_date: string|null # Date of round (YYYY-MM-DD)
source: string         # Source identifier (e.g., "dealpad", "GitHub Trending")
source_id: string|null # Source-specific ID
parsed_at: string      # ISO datetime when parsed
# Added by quick_score (optional, absent before scoring):
invest_score: int|null # 1-10
build_score: int|null  # 1-10
category: string|null  # Primary niche
one_liner: string|null # 1-sentence summary (Russian)
invest_rationale: string|null
build_rationale: string|null
```
Body: Markdown with startup name as H1, URL, round, description.

## 2_research/{slug}/

Directory per startup. Files:
- `website.md` — scraped website content with URL and scrape timestamp
- `web_research.md` — LLM-synthesized research summary (founders, business model, competitors, traction, risks)
- `profile.md` (future: full profile from TEMPLATE_profile.md)
- `github_metrics.md` (future: GitHub API data)
- `social_mentions.md` (future: HN/Reddit mentions)

## 3_analysis/{slug}_analysis.md

YAML frontmatter contract:
```yaml
name: string
url: string
invest_total: float     # Weighted score 0-10
build_total: float      # Weighted score 0-10
invest_verdict: string  # INVEST | WATCH | PASS
build_verdict: string   # BUILD | PARTNER | MONITOR | SKIP
analyzed_at: string     # ISO datetime
```
Body: Markdown with invest scoring (10 criteria), build scoring (8 criteria),
red/green flags, CIS adaptation, risks, next steps.

## digests/{YYYY-MM-DD}_weekly.md

No frontmatter. Sections:
- Pipeline Summary (counts at each stage)
- INVEST Candidates (score ≥ 8)
- WATCH List (6–7.9)
- BUILD Opportunities (build_score ≥ 6)
- Trends This Week
- All Scored Startups (full table)

## _archive/{YYYY-MM-DD}_{slug}.md

Same schema as 1_ideas/ plus:
```yaml
archived_at: string     # ISO datetime
archive_reason: string  # Why filtered out
```

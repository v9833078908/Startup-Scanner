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
# Added by pre-filter LLM classification:
is_tech: bool              # Is this a technology company?
sector: string             # Primary sector (e.g., "AI/ML", "fintech")
sector_match: string       # "yes" / "partial" / "no"
product_type: string       # "software" / "hardware" / "biotech" / "service" / "other"
b2b_b2c: string            # "b2b" / "b2c" / "both" / "unknown"
classification_status: string  # "classified" / "failed"
review_needed: bool|null   # true if LLM classification failed (fallback applied)
invest_eligible: bool      # sector_match yes/partial + is_tech (round is scoring factor, not gate)
build_eligible: bool       # sector_match yes/partial + software/service/unknown + is_tech
# Added by triage (binary evidence signals — NOT numeric scores):
invest_priority: string    # "high" / "medium" / "low" — from 4 binary signal count
build_candidate: bool      # type-level filter: is_tech + software/service + sector_match
has_product_evidence: bool  # Does description mention users, revenue, integrations?
has_founder_signal: bool    # Does description mention founder credentials?
barriers: list[string]     # 2-3 specific barriers/risks identified by LLM
one_liner: string|null     # 1-sentence summary (Russian)
category: string|null      # Specific niche string (e.g., "AI code review")
# Added by research gate (after research enrichment):
analysis_ready: bool       # Has enough evidence for expensive deep analysis
build_priority: string     # "high" (rare signal found) / "medium" (build candidate, no rare signal)
has_team_data: bool         # Research found specific founder/team info
has_traction_data: bool     # Research found revenue, users, growth data
has_competitive_context: bool  # Research found named competitors, market positioning
ru_gap_detected: bool       # No Russian/CIS competitor found
oss_commercializable: bool  # Open-source project with no clear monetization
cross_sell_fit: bool        # Product useful to iFree's B2B tech clients
underserved_niche: bool     # Fragmented market, no dominant leader
clear_localization_path: bool  # Adaptable for CIS market in <3 months
```

**Note:** `invest_score` and `build_score` do NOT exist in 1_ideas/ files.
They are only computed during deep analysis (Stage 6) and stored in 3_analysis/ files.

Body: Markdown with startup name as H1, URL, round, description.

## 2_research/{slug}/

Directory per startup. Files:
- `website.md` — scraped website content with URL and scrape timestamp
- `web_research.md` — LLM-synthesized research summary (founders, business model, competitors, traction, risks)
- `gate.md` — research gate evaluation results (invest evidence + build signals + analysis_ready decision)
- `profile.md` (future: full profile from TEMPLATE_profile.md)
- `github_metrics.md` (future: GitHub API data)
- `social_mentions.md` (future: HN/Reddit mentions)

### gate.md contract
```yaml
# Invest evidence (did research actually find useful data?)
has_team_data: bool         # Specific people or team details found
has_traction_data: bool     # Concrete numbers or named customers found
has_competitive_context: bool  # Specific competitors or market analysis found
# Build opportunity signals (rare signals detectable only after research)
ru_gap_detected: bool       # No established Russian/CIS competitor
oss_commercializable: bool  # Open-source, community-driven, no clear revenue model
cross_sell_fit: bool        # Product serves iFree's B2B tech client segment
underserved_niche: bool     # Fragmented market with no clear winner
clear_localization_path: bool  # Adaptable for CIS in <3 months
# Decision
analysis_ready: bool        # invest evidence >= 2/3 OR any rare build signal
build_priority: string      # "high" (rare signal) / "medium" (no rare signal)
```

## 3_analysis/{slug}_analysis.md

YAML frontmatter contract:
```yaml
name: string
url: string
invest_total: float     # Weighted score 0-10 (computed HERE, not at triage)
build_total: float      # Weighted score 0-10 (computed HERE, not at triage)
invest_verdict: string  # INVEST | WATCH | PASS
build_verdict: string   # BUILD | PARTNER | MONITOR | SKIP
analyzed_at: string     # ISO datetime
prompt_version: string  # Prompt file hash or version tag (e.g., "deep_analysis_v1")
model: string           # Model used for analysis (e.g., "openrouter/mistral-large")
```

**Note:** invest_total/build_total are the ONLY numeric scores in the pipeline.
They are computed by the heavy model with full research context -- not from thin triage data.

Body: Markdown with invest scoring (10 criteria), build scoring (8 criteria),
red/green flags, CIS adaptation, risks, next steps.

## digests/{YYYY-MM-DD}_weekly.md

No frontmatter. Sections:
- Pipeline Summary (counts at each stage, triage priority distribution)
- INVEST Candidates (invest_total >= 8, from 3_analysis/)
- WATCH List (6-7.9, from 3_analysis/)
- BUILD Opportunities (build_total >= 8, from 3_analysis/)
- Trends This Week
- All Analyzed Startups (full table)

## _archive/{YYYY-MM-DD}_{slug}.md

Same schema as 1_ideas/ plus:
```yaml
archived_at: string     # ISO datetime
archive_reason: string  # Why filtered out
```

## Task

Conduct deep research on the startup **{name}** ({url}).

**Context:** we are i-Free, a startup studio evaluating whether to build a localized analog in one of the target regions (CIS / MENA / SEA / LATAM). The output of this research feeds a downstream decision stage whose audience is leadership. They need to answer two questions: **"why this startup?"** and **"why now?"**. Your job is to produce the fact base that makes those answers possible — no verdict, no scoring, just facts with citations.

## Known inputs

- **Description:** {description}
- **Round:** {round_raw}
- **Category:** {category}
- **Triage LLM build thesis (internal hypothesis to validate):** {build_thesis}

> The triage hypothesis is a starting point, not a fact. Validate or refute it with data. Do not confirm it automatically. Do not reference the triage hypothesis or pipeline mechanics in your output — this research document is consumed by a downstream analysis stage, not by end users.

## Startup website excerpt (primary source)

Raw text extracted from **{url}** by our scraper. This is primary source material from the startup itself — use it as grounding for what the product actually does, pricing, ICP claims, and self-reported traction. Treat it as a primary source (like a press release), not as independent verification — still cross-check claims against third-party data. May be empty if the scraper failed; in that case proceed with your own web research.

{website_summary}

## Anti-hallucination rules (hard)

These rules override everything else. Violating them makes the research unusable.

- **Every number (TAM, revenue, users, growth %) must appear in the format:** `[value] ([source], [year])`. Without a source and year, do not write the number — write "no public data" instead.
- **Mark secondary sources explicitly.** If a figure comes from a blog re-telling a report rather than the report itself, append `(secondary source)`.
- **Do not aggregate TAM across reports without disclosure.** Bad: "TAM is $50B." Good: "Gartner estimates segment X at $12B (2024); Statista gives $18B for overlapping segment Y (2023); no direct estimate of the target segment exists."
- **Prefer primary sources for traction metrics:** Crunchbase, PitchBook, SEC filings, official press releases. Reddit / forum posts are acceptable only for user sentiment, never for traction numbers.
- **Never invent dates, round sizes, headcounts, or user counts.** If the data is not findable, write "no public data" and move on.

## What to research

### 1. Business substance (minimum 150 words)

- What the product actually does — mechanics, not buzzwords. A reader should be able to sketch the UI and the data flow from your description.
- What problem it solves and how acute the problem is — cite user evidence if available.
- Who pays (ICP — ideal customer profile), concrete use cases.
- Business model, pricing, ACV or typical deal size.

### 2. Market size (minimum 200 words)

- Bottom-up TAM estimate: number of potential customers × ACV. Show the arithmetic.
- Top-down TAM from analyst reports, with source and year. Reconcile with bottom-up if they diverge.
- Market dynamics: growing / flat / shrinking, with growth % and source.
- Key growth drivers or headwinds (regulatory changes, tech cost curves, behavioral shifts).

### 3. Competitive landscape (minimum 250 words, includes mandatory table)

Cover global players briefly, then spend most of the word budget on regional competition — this is what drives the `recommended_market` decision downstream.

**Required table — competitive status across 5 target regions:**

| Region       | Top-1 local competitor (name, URL) or "no local players" | Traction / share estimate | Gap status |
|--------------|----------------------------------------------------------|---------------------------|------------|
| Russia       | ...                                                      | ...                       | OCCUPIED / CONTESTED / GAP / UNKNOWN |
| CIS ex-RU    | ...                                                      | ...                       | ... |
| MENA         | ...                                                      | ...                       | ... |
| SEA          | ...                                                      | ...                       | ... |
| LATAM        | ...                                                      | ...                       | ... |

Gap status definitions:
- **OCCUPIED** — a local player has >30% share or dominant brand; new entrant cannot realistically displace within 24 months.
- **CONTESTED** — 2+ local players competing, none dominant; entry possible but requires differentiation.
- **GAP** — no meaningful local player; entry window open.
- **UNKNOWN** — public data insufficient. Use this honestly; do not guess.

Below the table, add 2–3 paragraphs on why dominance or absence exists in each relevant region (regulatory moat, distribution, language, cultural fit, prior attempts that failed).

### 4. Validation and traction of the original (minimum 150 words)

- Revenue, users, growth — if public.
- Hiring velocity from LinkedIn if observable.
- User reviews from G2, Capterra, Product Hunt, Reddit, industry forums — quote sentiment, not traction.
- Investors, their reputation, round size and structure. Flag if lead investor is top-tier (a16z, Sequoia, Lightspeed, Accel, YC, Founders Fund, Benchmark, Index).

### 5. Build feasibility for i-Free (minimum 200 words)

High-level overview only — downstream stages do not need work-package breakdowns. Cover:

- Technical complexity: what is under the hood, what stack is required, which third-party APIs are critical dependencies.
- Rough time to MVP (months) for a team of 3 fullstack + 1 ML engineer.
- Rough time to first revenue.
- Regulatory barriers per candidate target market (fintech licenses, health certification, data residency, etc.).
- 3–5 key risks of building an analog inside i-Free (be specific — "execution risk" is not a risk).

### 6. Geography recommendation (minimum 100 words)

- Which market makes sense for building an analog and why.
- Base on data from section 3: where demand exists, where the gap is, where entry is structurally easier.
- Do not default to CIS — if data points elsewhere, recommend elsewhere.
- **Negative space analysis:** if the recommended market has no local analog, answer explicitly why. Options: market too small, regulatory barriers, cultural mismatch, prior attempts failed (name them), or simply no one has tried yet. Without this, the geography recommendation is incomplete.

## Format

- **Length:** 800–1500 words total, respecting the per-section minimums above.
- **Language:** Russian. Technical terms and product / company names stay in English.
- **Citations:** every market, competitor, or traction claim must link to a source. Inline URLs or footnote-style references are both acceptable.
- **Missing data:** write "no public data" or "данные не найдены". Do not invent figures.
- **Structure:** use sections 1–6 as top-level headers in your output, in order.
- **No verdict:** scoring and verdict are produced by a downstream stage. Your job is the fact base.

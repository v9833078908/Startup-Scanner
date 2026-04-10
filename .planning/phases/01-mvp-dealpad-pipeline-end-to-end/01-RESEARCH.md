# Phase 1: MVP — DealPad Pipeline End-to-End - Research

**Researched:** 2026-04-10
**Domain:** Python async pipeline, Telegram HTML export parsing, OpenRouter LLM API, YAML frontmatter, web scraping
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| R1 | Project setup: venv, .env, dirs, dependencies | Standard Python project setup — no blockers |
| R2 | Config files: filters.yaml, scoring_weights.yaml | Fully specified in MVP_Plan.md; pyyaml covers reading |
| R3 | DealPad HTML parser: parse div.message.default.clearfix, extract fields, save MD | Telegram export structure CONFIRMED; selectors verified via two independent parsers |
| R4 | Pre-filter: read 1_ideas/, apply filters.yaml, archive rejects | python-frontmatter 1.1.0 handles YAML frontmatter read/write cleanly |
| R5 | LLM Quick Score: async OpenRouter light model, 5 concurrent, append to frontmatter | asyncio.Semaphore pattern confirmed; OpenRouter + openai SDK confirmed |
| R6 | Deep Research: scrape website, web search via OpenRouter, save to 2_research/ | httpx + BS4 pattern confirmed; OpenRouter web search approach clarified below |
| R7 | Deep Analysis: heavy model full scoring, save to 3_analysis/ | Same async pattern; response_format json_object or json_schema both supported |
| R8 | Digest + orchestrator: run_pipeline.py --html, idempotent steps | No technical blockers; string formatting + file I/O |
</phase_requirements>

---

## Summary

The DealPad pipeline is a six-stage sequential Python script that transforms a Telegram Desktop HTML export into a structured weekly investment digest. The pipeline is file-system native — no database, no server, only Markdown files and YAML frontmatter as the data layer.

The two most technically specific areas requiring careful implementation are: (1) the Telegram HTML export parser, where the exact CSS selectors are confirmed by multiple independent community parsers, and (2) the async LLM layer, where the standard asyncio.Semaphore + asyncio.gather() pattern with exponential backoff is well-established for OpenRouter.

The MVP plan in docs/MVP_Plan.md is complete and correct. The planner's job is primarily to translate it into concrete executable tasks, not to design new architecture. The biggest implementation risk is the OpenRouter "web search" step in R6 — OpenRouter is an LLM router, not a search engine, so "web search" must be done either by calling an LLM with a web-browsing tool, or by scraping common sources. This needs a concrete plan.

**Primary recommendation:** Follow MVP_Plan.md exactly. Use `python-frontmatter` for YAML frontmatter, `asyncio.Semaphore(5)` + `asyncio.gather()` for LLM concurrency, `div.message.default.clearfix` selector for Telegram HTML, `dateparser` for Russian date strings, and a simple regex for currency normalization. Implement "web search" in R6 as a website-only scrape for MVP scope — skip the LLM web search unless OpenRouter search-enabled models are used.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | >=1.0 | OpenRouter API client (base_url override) | Confirmed in decisions; OpenAI-compatible interface |
| httpx | >=0.27 | Async HTTP for website scraping | Project standard per CLAUDE.md |
| beautifulsoup4 | >=4.12 | HTML parsing: Telegram export + website content | Project standard per CLAUDE.md |
| pyyaml | >=6.0 | Parse config/filters.yaml, config/scoring_weights.yaml | Project standard per CLAUDE.md |
| python-dotenv | >=1.0 | Load .env secrets | Project standard per CLAUDE.md |
| python-frontmatter | 1.1.0 | Read/write YAML frontmatter in MD files | Best-in-class dedicated library; avoids rolling own parser |
| dateparser | >=1.2 | Parse Russian date strings like "13 января 2023" | Supports 200+ locales including Russian; handles Cyrillic months |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lxml | >=5.0 | Faster BS4 HTML parser backend | Use as BS4 parser for speed on 430-message file |
| html.parser | stdlib | BS4 parser fallback | Available without install; slower |
| re | stdlib | Regex for round parsing, currency extraction | Currency normalization is simple regex, no library needed |
| asyncio | stdlib | Concurrency control via Semaphore | Core pattern for parallel LLM calls |
| pathlib | stdlib | File path handling | Cleaner than os.path for directory ops |
| json | stdlib | Parse LLM JSON responses | Prefer over eval() always |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-frontmatter | manual YAML split + pyyaml | python-frontmatter preserves content structure; avoids edge cases with YAML delimiters in text |
| dateparser | rutimeparser, manual dict | dateparser is maintained, well-tested, handles format variations; manual dict breaks on edge cases |
| asyncio.Semaphore | tenacity-only retries | Semaphore controls concurrency; tenacity handles retries — need both together |

**Installation:**
```bash
pip install openai httpx "beautifulsoup4[lxml]" pyyaml python-dotenv python-frontmatter dateparser lxml
```

---

## Architecture Patterns

### Recommended Project Structure
```
scouting-pipeline/
├── .env                         # OPENROUTER_API_KEY, OPENROUTER_MODEL_LIGHT, OPENROUTER_MODEL_HEAVY
├── .gitignore
├── requirements.txt
├── config/
│   ├── filters.yaml
│   └── scoring_weights.yaml
├── prompts/
│   ├── quick_score.md
│   ├── deep_analysis.md
│   └── digest.md
├── scouts/
│   └── dealpad_parser.py
├── pipeline/
│   ├── prefilter.py
│   ├── quick_score.py
│   ├── deep_research.py
│   ├── deep_analysis.py
│   └── digest_generator.py
├── lib/
│   ├── llm.py
│   ├── scraper.py
│   └── utils.py
├── run_pipeline.py
├── 1_ideas/
├── 2_research/
├── 3_analysis/
├── _archive/
└── digests/
```

### Pattern 1: Telegram HTML Export Parsing

**What:** Select `div.message.default.clearfix` elements; extract content from child elements by class.

**Confirmed by:** Two independent community parsers (mrtj/gist, KanegaeGabriel/telegram-export-converter) use this exact structure. The craftamap/telegram-export-parser uses `.message.default` selector.

**Key HTML structure:**
```
<div class="message default clearfix" id="message{ID}">
    <div class="pull_right date details" title="DD.MM.YYYY HH:MM:SS">...</div>
    <div class="from_name">...</div>
    <div class="text">
        <a href="URL">Startup Name</a>
        <br>
        Раунд: $XXX, Month YYYY
        <br>
        Description text...
    </div>
</div>
```

**"Joined" messages** (continuation from same sender) have class `message default clearfix joined` — content is in same `.text` div but there is no `.from_name`. For DealPad channel posts this is less relevant since the channel bot is always the sender.

**Example:**
```python
# Source: mrtj gist + KanegaeGabriel telegram-export-converter (verified)
from bs4 import BeautifulSoup

with open("messages.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "lxml")

messages = soup.select("div.message.default.clearfix")
for msg in messages:
    msg_id = msg.get("id", "")
    date_el = msg.find("div", class_="date")
    date_str = date_el["title"] if date_el else ""  # "DD.MM.YYYY HH:MM:SS"
    text_el = msg.find("div", class_="text")
    if not text_el:
        continue
    links = text_el.find_all("a")
    name = links[0].get_text(strip=True) if links else ""
    url = links[0]["href"] if links else ""
    full_text = text_el.get_text(separator="\n", strip=True)
```

**Spam filter:** Skip if text contains "обзоры" or "fastfounder" (case-insensitive check on raw text).

**Multi-file exports:** Telegram Desktop splits long channels into `messages.html`, `messages2.html`, etc. The orchestrator should accept a glob pattern or a directory, not just a single file. This is an important edge case — 430 messages may span multiple files.

### Pattern 2: Async LLM Calls with Concurrency Control

**What:** `asyncio.Semaphore(N)` limits concurrent in-flight requests; `asyncio.gather(*tasks, return_exceptions=True)` runs them concurrently.

**When to use:** All LLM pipeline steps (quick_score, deep_analysis, digest).

```python
# Source: standard asyncio + openai async client pattern (MEDIUM confidence — well documented)
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
semaphore = asyncio.Semaphore(5)  # 5 concurrent requests per REQUIREMENTS.md

async def score_one(idea: dict) -> dict:
    async with semaphore:
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(
                    model=os.getenv("OPENROUTER_MODEL_LIGHT"),
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)  # exponential backoff

async def score_all(ideas: list[dict]) -> list[dict]:
    tasks = [score_one(idea) for idea in ideas]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Pattern 3: YAML Frontmatter Read/Write

**What:** python-frontmatter 1.1.0 for all MD file I/O.

```python
# Source: pypi.org/project/python-frontmatter verified
import frontmatter

# Read
post = frontmatter.load("1_ideas/2024-01-15_acme.md")
name = post["name"]
content = post.content

# Update frontmatter
post["invest_score"] = 7
post["build_score"] = 8
post["category"] = "fintech"

# Write back (preserves content)
with open("1_ideas/2024-01-15_acme.md", "w", encoding="utf-8") as f:
    f.write(frontmatter.dumps(post))
```

**Key:** `frontmatter.dumps()` preserves the `---` delimiters and content body. Do not use pyyaml directly for this — it won't preserve the content section.

### Pattern 4: Website Text Extraction

**What:** httpx async fetch + BS4 decompose unwanted tags + get_text().

```python
# Source: BS4 docs + httpx docs (MEDIUM confidence)
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

async def scrape_website(url: str) -> str:
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()
        except Exception:
            return ""

    soup = BeautifulSoup(resp.text, "lxml")
    # Remove boilerplate
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Truncate to keep LLM tokens reasonable (~2000 chars)
    return text[:3000]
```

### Pattern 5: Round Amount Normalization

**What:** Pure regex — no external library needed. Handles $K/$M/$B and € prefix.

```python
# Source: custom (standard regex approach — HIGH confidence for this scope)
import re

MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
# Approximate EUR→USD (use static 1.08 for MVP — exact rate not needed)
CURRENCY_TO_USD = {"$": 1.0, "€": 1.08, "£": 1.27, "₽": 0.011}

def parse_round_usd(raw: str) -> int | None:
    """Parse '$115K' → 115000, '€4M' → 4320000, '$1.5B' → 1500000000"""
    if not raw:
        return None
    match = re.search(r"([$€£₽])\s*([\d.]+)\s*([KMBkmb])?", raw)
    if not match:
        return None
    symbol, amount_str, suffix = match.groups()
    amount = float(amount_str)
    if suffix:
        amount *= MULTIPLIERS.get(suffix.upper(), 1)
    usd_rate = CURRENCY_TO_USD.get(symbol, 1.0)
    return int(amount * usd_rate)
```

### Pattern 6: Russian Date Parsing

**What:** `dateparser` handles Cyrillic month names automatically.

```python
import dateparser

def parse_russian_date(text: str) -> str | None:
    """Parse '13 января 2023' or 'January 2023' → '2023-01-13'"""
    dt = dateparser.parse(text, languages=["ru", "en"])
    if dt:
        return dt.strftime("%Y-%m-%d")
    return None
```

**Fallback:** If dateparser is unavailable, a manual dict of Cyrillic months works but is brittle. Use dateparser.

### Anti-Patterns to Avoid

- **Don't use `json.loads()` on raw LLM output without try/except.** Models occasionally produce trailing commas or markdown code fences. Wrap in try/except and retry on parse failure.
- **Don't move ideas to _archive/ by deleting and recreating.** Use `shutil.move()` to preserve file identity.
- **Don't hardcode model names in pipeline scripts.** Read from `os.getenv("OPENROUTER_MODEL_LIGHT")` per CLAUDE.md.
- **Don't use `asyncio.run()` inside a function that is already async.** The orchestrator `run_pipeline.py` should call async steps via a single top-level `asyncio.run(main())`.
- **Don't skip `return_exceptions=True` in gather().** Without it, a single failed LLM call crashes the entire batch.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter parsing | Custom regex splitter on `---` | python-frontmatter | Edge cases: YAML values with `---` in them, multiline strings, encoding |
| Russian date parsing | Manual Cyrillic month dict | dateparser | Covers abbreviations, whitespace variants, year-only formats |
| HTTP retry with backoff | Custom sleep loop | openai SDK built-in (2 retries) + manual wrapper for 3rd | OpenAI SDK already retries 408, 429, 5xx twice |
| JSON output from LLM | Regex on free text | `response_format={"type": "json_object"}` | Model stays in JSON mode; far more reliable |
| Async HTTP client | requests in thread pool | httpx.AsyncClient | httpx is already the project standard; purpose-built async |

**Key insight:** The pipeline's LLM layer is the complexity. Everything else (file I/O, YAML, HTTP) is commodity — use the standard library where possible and dedicated small libraries otherwise.

---

## Common Pitfalls

### Pitfall 1: Telegram Multi-File Export
**What goes wrong:** Telegram Desktop splits channels with many messages into `messages.html`, `messages2.html`, `messages3.html`, etc. If you only parse `messages.html`, you get a fraction of the ~430 expected entries.
**Why it happens:** Telegram caps ~1000 messages per file for performance in the browser.
**How to avoid:** Accept a directory path OR a glob pattern in `run_pipeline.py`. Detect sibling files automatically: `sorted(Path(html_path).parent.glob("messages*.html"))`.
**Warning signs:** Parsed count significantly below 430 (~100-150 is a red flag).

### Pitfall 2: LLM Returns Invalid JSON
**What goes wrong:** Even with `response_format={"type": "json_object"}`, some models occasionally produce JSON wrapped in markdown code fences (` ```json ... ``` `), or with trailing commas.
**Why it happens:** Model follows instruction imperfectly; json_object mode is a best-effort hint on some providers/models.
**How to avoid:** Strip code fences before parsing: `text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE)`. Retry once on json.JSONDecodeError.
**Warning signs:** JSONDecodeError in quick_score step.

### Pitfall 3: Website Scraping Timeouts Block the Batch
**What goes wrong:** One slow or unresponsive website hangs the async scraper for 15+ seconds, and if not properly handled, blocks all concurrent tasks.
**Why it happens:** httpx default timeout may be too generous; some startup URLs are dead.
**How to avoid:** Use `httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))`. Catch `httpx.TimeoutException` and `httpx.RequestError` separately; log and continue. Store empty string to `website.md` for failed scrapes.
**Warning signs:** Deep research step takes >5 minutes per startup.

### Pitfall 4: Idempotency — Re-running Overwrites Scores
**What goes wrong:** Re-running `run_pipeline.py` re-parses all DealPad messages, creating duplicates in `1_ideas/` or overwriting edited frontmatter.
**Why it happens:** No existence check before writing.
**How to avoid:** In the parser, check `if Path(output_path).exists(): continue`. In quick_score, check if `invest_score` key already exists in frontmatter before calling LLM. Each step should be a no-op for already-processed items.
**Warning signs:** 1_ideas/ doubles in size on second run.

### Pitfall 5: Pre-filter Keyword Matching Too Broad
**What goes wrong:** Matching "AI" in include_niches also matches "rail", "wait", "detail" because substring matching is naive.
**Why it happens:** Case-insensitive `in` operator matches substrings.
**How to avoid:** Use word-boundary regex or split description into words and match: `re.search(r'\bAI\b', description, re.IGNORECASE)`. Or at minimum use `' ' + keyword.lower() + ' '` padding on the description.
**Warning signs:** Too many passes (~300+ instead of ~60-100) or filtering out obvious matches.

### Pitfall 6: OpenRouter "Web Search" Is Not Built-In
**What goes wrong:** The MVP plan says "web search via OpenRouter" for deep research. OpenRouter is an LLM router, not a search engine — it does not have native web search.
**Why it happens:** Confusion between OpenRouter model capabilities (some models have search tools) and OpenRouter platform search.
**How to avoid (MVP approach):** For MVP scope, limit deep research to website scraping only. Skip web search. The LLM prompt in deep_analysis can ask the model to reason from the scraped content + what it knows. Label `web_research.md` as "LLM summary from training data" with a disclaimer. Real web search can be Phase 2+ using Brave Search API or SerpAPI.
**Warning signs:** Trying to pass a search query to `client.chat.completions.create()` and expecting Google results.

---

## Code Examples

Verified patterns from official sources:

### OpenRouter Setup
```python
# Source: openrouter.ai/docs/quickstart (HIGH)
import os
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
```

### JSON Output from OpenRouter
```python
# Source: openrouter.ai/docs/guides/features/structured-outputs (HIGH)
response = await client.chat.completions.create(
    model=os.getenv("OPENROUTER_MODEL_LIGHT"),
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
    temperature=0.1,
)
raw = response.choices[0].message.content
# Strip markdown fences if present
raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
data = json.loads(raw)
```

### Concurrency-Limited Batch
```python
# Source: asyncio stdlib docs + standard LLM batch pattern (HIGH)
import asyncio

sem = asyncio.Semaphore(5)

async def process_one(item):
    async with sem:
        return await call_llm(item)

results = await asyncio.gather(
    *[process_one(x) for x in items],
    return_exceptions=True
)
# Filter out exceptions
successes = [r for r in results if not isinstance(r, Exception)]
```

### Slug Generation
```python
# Source: custom (standard pattern — HIGH)
import re, unicodedata

def make_slug(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[-\s]+", "-", name).strip("-")[:50]
```

### Writing a New Idea MD File
```python
# Source: python-frontmatter 1.1.0 docs (HIGH)
import frontmatter
from datetime import datetime

post = frontmatter.Post(
    content=f"# {name}\n\n**URL:** {url}\n**Round:** {round_raw}\n**Description:** {description}",
    name=name,
    url=url,
    round_usd=round_usd,
    round_raw=round_raw,
    round_date=round_date,
    source="dealpad",
    source_id=message_id,
    parsed_at=datetime.utcnow().isoformat(),
)
with open(output_path, "w", encoding="utf-8") as f:
    f.write(frontmatter.dumps(post))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests + threading for parallel HTTP | httpx.AsyncClient + asyncio | 2022+ | Lower resource use, simpler code |
| json_object response_format only | json_schema with strict mode also available | 2024 | Can enforce exact field names and types |
| Gemini 1.5 Flash as light model | Gemini 2.0 Flash ($0.10/$0.40 per M tokens) | Feb 2025 | Cheaper, faster, 1M context |
| Separate dateutil for date parsing | dateparser for multilingual | Ongoing | Better for Russian/CIS content |

**Current light model recommendation:** `google/gemini-2.0-flash-001` — $0.10/$0.40 per M tokens, 1M context, fastest TTFT. Note: being deprecated June 1, 2026 (after MVP deadline — not a concern).

**Current heavy model recommendation:** `anthropic/claude-sonnet-4-5` or `google/gemini-2.5-flash` — better reasoning for multi-criteria scoring.

**Deprecated/outdated:**
- `openai/gpt-3.5-turbo` for quick scoring: inferior instruction following vs Gemini Flash at higher cost
- `feedparser` + polling for web search: not applicable for MVP scope

---

## Open Questions

1. **DealPad export is single or multi-file?**
   - What we know: Telegram splits exports at ~1000 messages per file; 430 messages may fit in one file
   - What's unclear: Whether the actual DealPad export available is one file or multiple
   - Recommendation: Implement multi-file support defensively (glob `messages*.html`); costs 2 lines

2. **"Web search" in Deep Research — what model to use?**
   - What we know: OpenRouter routes to models; some models (Perplexity, etc.) have built-in search. Standard models do not.
   - What's unclear: Whether the pipeline should call a search-enabled model or skip web search entirely
   - Recommendation: For MVP, implement deep_research as website-scrape only + LLM knowledge synthesis. Document clearly in `web_research.md` header. Real search = Phase 2.

3. **Round parsing from DealPad format — exact text format?**
   - What we know: MVP plan says "parse 'Раунд: $XXX, DATE' line"
   - What's unclear: Whether DealPad consistently uses this format or has variants
   - Recommendation: Implement regex with fallback to `round_raw=None`; log unparseable entries for manual review

4. **EUR/GBP/RUB to USD conversion rate**
   - What we know: DealPad announces European and Russian startups using local currencies
   - What's unclear: Whether a static rate or live rate is expected
   - Recommendation: Use static rates for MVP ($1 = €0.92, £0.79, ₽90) — precision not needed for filtering

---

## Sources

### Primary (HIGH confidence)
- openrouter.ai/docs/quickstart — Python SDK setup, base_url override
- openrouter.ai/docs/guides/features/structured-outputs — response_format json_object/json_schema
- openrouter.ai/google/gemini-2.0-flash-001 — pricing $0.10/$0.40 per M, 1M context
- pypi.org/project/python-frontmatter — version 1.1.0, load/dumps API
- mrtj gist (gist.github.com/mrtj/049024345d37ed625e923abb267dc396) — Telegram HTML selector `div.message.default`
- KanegaeGabriel telegram-export-converter — confirms `div.message.default.clearfix`, `div.pull_right.date.details[title]`
- craftamap telegram-export-parser — confirms `.message.default` + `.text` + `.date` + `.from_name`
- python-httpx.org — AsyncClient, timeout configuration

### Secondary (MEDIUM confidence)
- pypi.org/project/dateparser — Russian date parsing, Cyrillic month support
- rednafi.com/python/limit-concurrency-with-semaphore — asyncio.Semaphore concurrency pattern
- openrouter.ai/docs/api/reference/limits — rate limits (paid users: no specific cap documented; 429 auto-retried by SDK)

### Tertiary (LOW confidence)
- Static EUR→USD rate (1.08) — approximate; not fetched from live API
- "Web search via OpenRouter" interpretation — needs clarification from user or implementation decision

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are project-specified or verified via official sources
- Telegram parsing selectors: HIGH — confirmed by 3 independent community parsers
- Architecture: HIGH — fully specified in MVP_Plan.md; no design decisions needed
- OpenRouter async pattern: HIGH — openai SDK + asyncio.Semaphore is well-documented standard
- Pitfalls: MEDIUM — derived from code analysis and community patterns; some edge cases may be environment-specific
- "Web search" in R6: LOW — ambiguous in spec; interpretation and resolution documented above

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (30 days — libraries stable; OpenRouter model deprecations possible but noted)

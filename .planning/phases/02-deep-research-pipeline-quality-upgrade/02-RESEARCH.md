# Phase 2: Deep Research + Pipeline Quality Upgrade — Research

**Researched:** 2026-04-14
**Domain:** Parallel AI Task API integration + pipeline modification (Python, asyncio, httpx)
**Confidence:** HIGH (all code verified from source files; API details verified from official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use Parallel AI Task API (https://api.parallel.ai/v1/tasks/runs) for deep research
- Processor: start with `core` ($0.025/run), downgrade to `base` ($0.005/run) if budget tight
- Auth: `PARALLEL_API_KEY` env var, header `x-api-key`
- Workflow: POST create task → poll GET result (timeout 600s default)
- Output schema: `type: "text"` for markdown research report with citations
- Budget: ~$50/week, ~20 startups max → ~$2.50/startup
- Stage 7.5: new `pipeline/deep_research_v2.py` + `lib/parallel_client.py`
- Stage 8: modify `pipeline/deep_analysis.py` + `prompts/deep_analysis.md` — build-only, kill signals, executive summary
- Stage 9: modify `pipeline/digest_generator.py` + `prompts/digest.md`
- Invest scoring removed from Stage 8 (anchoring fix) — build-only architecture
- Kill signals checked BEFORE scoring; killed=True forces verdict PASS
- Concurrency: asyncio semaphore (3-5 concurrent)
- Idempotency: skip if deep_research.md already exists

### Claude's Discretion
- Exact implementation of parallel_client.py (httpx async vs `parallel` Python SDK)
- Error handling strategy for Parallel AI API failures (retry logic, fallback)
- Exact semaphore count for concurrent deep research requests
- Exact prompt wording

### Deferred Ideas (OUT OF SCOPE)
- Few-shot examples (needs manual labeling from Дина + Илья)
- B2C segment support
- Multi-agent architecture / LangChain refactor
- A/B testing across multiple research APIs
</user_constraints>

---

## Summary

The plans (02-01, 02-02, 02-03) are substantially correct. They accurately reflect the code structure and integrate properly with the existing pipeline. This research validates the approach, corrects several specific technical details, and surfaces four issues that need attention before execution begins.

**Primary recommendation:** Proceed with plans as written but apply the four corrections identified in the Architecture Validation section below. The most significant one: the Parallel AI Python SDK (`parallel-web`) is available and well-suited — but raw `httpx` is still the better choice here given the project pattern. The second: the `output.basis` citations structure is more nested than the plans assume and needs the correct extraction path.

---

## Architecture Validation

### Question 1: SDK vs raw httpx for parallel_client.py

**Finding:** The official `parallel-web` SDK (v0.4.2, March 2026) exists on PyPI. It provides `Parallel` (sync) and `AsyncParallel` (async) clients with `client.task_run.create()` and `client.task_run.result()`. It handles retries (`max_retries=2` default) and has typed exception classes (`RateLimitError`, `AuthenticationError`, etc.).

**Recommendation (Claude's discretion): use raw httpx, not the SDK.** Reasons:
1. The project has no other SDK dependencies — all external APIs use raw httpx (see `lib/exa_client.py` uses `exa-py` SDK as the one exception, and it's wrapped in `asyncio.to_thread` because exa-py is synchronous). [VERIFIED: lib/exa_client.py line 8]
2. `parallel-web` would need adding to `requirements.txt`, adding a dependency the plans never mention.
3. The `httpx` pattern (as in `lib/web_search.py`'s `_ddg_search` and `_sonar_search`) is already established.
4. The SDK wraps the same REST endpoints — no functionality advantage for this use case (no streaming, no complex state management).

**If SDK is used instead:** install `parallel-web>=0.4.2`, use `AsyncParallel` not `Parallel`, and `client.task_run.result()` blocks internally — pass `api_timeout=600`. SDK auto-reads `PARALLEL_API_KEY` from env. [VERIFIED: pypi.org/project/parallel-web]

**Confirmed:** httpx is version 0.28.1 in the venv. [VERIFIED: runtime check]

### Question 2: Concurrency — is Semaphore(3) appropriate?

**Finding:** The Parallel AI rate limit is 2,000 POST requests per minute (only POST /tasks/runs counts, GET /result does not). [VERIFIED: docs.parallel.ai/getting-started/rate-limits]

With 20 startups maximum per run, even Semaphore(20) would not approach rate limits. The semaphore is needed to control **cost and latency**, not rate limits.

**Recommendation:** Semaphore(3) is correct. At `core` processor, tasks take 60s–5 minutes each. With 3 concurrent at ~2 minutes average = ~7 minutes for 20 startups. That is reasonable. Semaphore(5) would also be fine. The plans' choice of Semaphore(3) is safe. [VERIFIED: docs.parallel.ai/task-api/guides/choose-a-processor for timing ranges]

### Question 3: Processor tiers — base vs core vs pro

**Verified pricing (per task run):**
- `lite`: $0.005/run (10-60 seconds, ~2 output fields)
- `base`: $0.005/run (15-100 seconds, ~5 output fields)
- `core`: $0.025/run (60s–5 min, ~10 output fields)
- `pro`: $0.10/run (2-10 min, ~20 output fields, exploratory web research)
- `ultra`: $0.30/run (5-25 min, deep multi-source research)

[VERIFIED: docs.parallel.ai/getting-started/pricing]

**Note — pricing correction from CONTEXT.md:** CONTEXT.md says `base=$0.005` AND `core=$0.025` — this matches the verified numbers. However the CONTEXT.md description says "base ($0.005)" appears to be correct. `lite` is also $0.005 but handles only ~2 fields. Do not use `lite` for startup research.

**For 800-1500 word startup research reports:** `core` is the correct tier. It handles "cross-referenced, moderately complex outputs" with ~10 output fields in 60s–5 minutes. `base` at $0.005 handles only ~5 fields and 15-100 seconds — likely insufficient depth for 6-section research briefs.

**Budget math at `core`:** 20 startups × $0.025 = $0.50 per pipeline run. Well within $50/week budget. `pro` at $0.10/run = $2.00 for 20 startups — still within budget and would give better research depth if quality proves insufficient with `core`.

**Recommendation:** Start with `core`. The "downgrade to base if budget tight" option in CONTEXT.md is valid but `base` may produce shallow 5-field results, not the 6-section 800-1500 word brief. Better budget lever: switch to `core` initially, reduce to `base` only if results are acceptable.

### Question 4: Idempotency for failed deep research runs

**Current plan behavior:** If Parallel AI fails (API error, timeout, empty content), `run_deep_research_task` returns `{"content": "(Deep research failed: ...)", "citations": []}` and `deep_research.md` is written with this stub content. On re-run, idempotency check (`if deep_research.md exists: skip`) means the stub is never retried.

**Finding:** This is a potential quality issue. A stub deep_research.md with `(Deep research failed: ...)` will cause Stage 8 to run analysis on empty deep_research_content — falling back to the old scarce-data behavior. The analysis will be low-quality but not crash.

**Recommendation:** The plan's "skip" behavior is correct for the demo deadline. For production, consider: write to a `.tmp` file, rename to `deep_research.md` only on success. Failed stubs could use a `deep_research_failed.md` name to allow retry. However, this is NOT required for Phase 2 — the fallback is acceptable.

**No plan revision needed.** But document this in the plan as a known limitation: stubs from failed API calls block retries until manually deleted.

### Question 5: Stage 7.5 wiring — `build_ready` variable name

**Verified from run_pipeline.py lines 243:** `build_ready = build_gate_result.get("build_analysis_ready_slugs", [])` — confirmed.

**Plan 02-03 Task 2 action uses `build_ready`** in the Stage 7.5 insertion code. This matches the actual variable name. No discrepancy. [VERIFIED: run_pipeline.py line 243]

### Question 6: Frontmatter migration — invest_* fields in existing files

**Verified:** All 11 existing analysis files in `3_analysis/` have exactly these fields:
`analyzed_at, build_total, build_verdict, invest_total, invest_verdict, name, url`

**These files will still be on disk** when Plan 02-02 and 02-03 execute (unless `--reset` was run). The digest generator will read them alongside any new build-only analysis files.

**Verified in digest_generator.py:**
- Line 106: `"invest_total": post.get("invest_total", 0)` — uses `.get()` with default. Safe.
- Line 107: `"build_total": post.get("build_total", 0)` — safe.
- Line 108: `"invest_verdict": post.get("invest_verdict", "PASS")` — safe.
- Line 109: `"build_verdict": post.get("build_verdict", "SKIP")` — safe.

**However:** `build_digest_manually()` uses `invest_candidates = [a for a in analyses if a["invest_verdict"] == "INVEST"]` (line 165) and builds an "INVEST Candidates" section. With `invest_verdict` defaulting to "PASS" for new build-only files, this section will always be empty — which is correct behavior. Plan 02-03 rewrites this function entirely, so this is not a regression risk.

**New fields added by Plan 02-02 that Plan 02-03 must read:** `killed`, `kill_reason`, `executive_summary`, `recommended_market`, `time_to_mvp`, `time_to_revenue`. These will be absent from old analysis files. Plan 02-03 explicitly uses `.get()` with defaults for all — confirmed correct pattern.

### Question 7: Body markdown change — downstream consumers

**Finding:** The only consumers of analysis file body content are:
1. `digest_generator.py` — `_extract_section()` used to extract "Invest Score" and "CIS Adaptation" sections (lines 200, 252)
2. Human readers in the file system

**Plan 02-03 rewrites `build_digest_manually()`** to no longer call `_extract_section()` for invest score — it instead uses the new `executive_summary` frontmatter field. The `cis_adaptation` body section is replaced by `recommended_market` frontmatter.

**Remaining risk:** The `_extract_section()` function (lines 133-146) is not deleted by any plan. It remains in `digest_generator.py`. If old analysis files are still present after reset, and the LLM-based path is used (not the manual fallback), the LLM gets the full analysis JSON including the old body content with "Invest Score" and "CIS Adaptation" sections. This is benign — the new digest prompt instructs the LLM to ignore numeric scores.

**No plan revision needed.** `_extract_section()` can be left in place as dead code until a cleanup phase.

### Question 8: Prompt template variables — .replace() vs .format()

**Verified from STATE.md:** "[Phase 01]: .replace() not .format() for prompts (literal JSON braces)" [VERIFIED: STATE.md line 64]

**Verified from build_research.py pattern:** All substitutions use `.replace("{var}", value)` — never `.format()`. [VERIFIED: build_research.py lines 77-79]

**Plans 02-01 and 02-02 both specify `.replace()` pattern explicitly.** No discrepancy.

**One edge case:** The deep_analysis prompt spec in `docs/Deep Analysis Upgrade Plan.md` contains a JSON example block in the response format section with literal `{signal_name: ...}` syntax. This is fine because: (a) the JSON example uses curly braces only as display text in the prompt, not as Python template variables, and (b) `.replace()` only substitutes exact `{variable_name}` strings that match the specific variable names being substituted. The JSON example braces won't match `{name}`, `{url}`, etc. [VERIFIED: confirmed pattern is safe]

### Question 9: Token budget — deep_research_content truncation

**Current analyze_one truncations (deep_analysis.py lines 79-81):**
- `website_content[:3000]`
- `research_notes[:3000]`

**Plan 02-02 adds:** `deep_research_content[:8000]`

**Total injected content:** ~14,000 characters of variable content + prompt template text (est. ~2,000 chars). Rough total prompt: ~16,000 characters ≈ ~4,000-5,000 tokens.

**Model being used:** `OPENROUTER_MODEL_HEAVY=google/gemini-2.5-pro` (verified from .env.example). Gemini 2.5 Pro has a 1M token context window. This truncation budget is trivially small relative to model capacity. [VERIFIED: .env.example line 3]

**Recommendation:** The 8,000 char truncation for `deep_research_content` is appropriate and safe. Gemini 2.5 Pro will not have context overflow issues even with full un-truncated content, but 8,000 chars covers an 800-1500 word report comfortably (1500 words ≈ 7,500-10,000 characters depending on word length).

**One edge case:** If `deep_research_content` is a stub failure string like `"(Deep research failed: Connection timeout)"`, the truncation has no effect and the LLM will do analysis without rich data — same as before Phase 2. This is the acceptable fallback identified in Question 4.

### Question 10: Test data availability

**Verified:** 20 existing research directories in `2_research/` with `build_research.md` files. 11 with `gate_build.md`. 11 of those have `build_analysis_ready: True`. [VERIFIED: runtime check]

**Verified slug names of build-ready startups:**
`atlas, blocks, deeptrace, electrifi-mobility, eshot-labs, lucky, monetary-metals, moonbounce, natter, ricerca, zanskar-securities`

**These are available as test data for Stage 7.5 dry-run.** Running `pipeline/deep_research_v2.py` directly with `slugs=["deeptrace"]` will produce one `deep_research.md` for validation before a full run.

**Important:** These 11 slugs do NOT yet have `deep_research.md` files — they only have `build_research.md` and `gate_build.md`. Stage 7.5 will process all 11 on first run. Good for demo.

---

## Implementation Pitfalls

### Pitfall 1: Parallel AI SDK vs httpx — `x-api-key` header

**What goes wrong:** The CONTEXT.md spec says auth header is `x-api-key`. The official SDK auto-handles this. If using raw httpx, the header must be set explicitly:
```python
headers={"x-api-key": api_key}
```
Not `Authorization: Bearer {key}` (which is the OpenRouter pattern). Using the wrong header returns 401.

**Prevention:** Plan 02-01 specifies `x-api-key` header explicitly in the task description. Confirm this is in the actual implementation.

### Pitfall 2: `output.basis` citations — nested structure

**What goes wrong:** CONTEXT.md says: `output.basis` contains `{field, reasoning, citations: [{url, title, excerpts}], confidence}`. The plan's citation extraction code iterates over `output.basis` expecting each item to be a citation with `url` and `title` fields.

**Actual structure (from OpenAPI spec):** `output.basis` is an array of "basis items" — each basis item covers one output field and contains `citations` as a nested array. The plan's citation formatting loop needs to iterate two levels:
```python
# Plan assumes (WRONG):
for citation in result["output"]["basis"]:
    url = citation["url"]  # KeyError!

# Correct structure:
for basis_item in result["output"]["basis"]:
    for citation in basis_item.get("citations", []):
        url = citation["url"]
        title = citation["title"]
```

**Risk level: HIGH — will cause KeyError at runtime if not corrected.**

Plan 02-01 Task 1 says "citations are extracted from output.basis" — but the extraction code must handle the nested structure. The executor must implement the two-level loop.

### Pitfall 3: `run_deep_research_v2` — route filter for "both" slugs

**What goes wrong:** The plan says "check route is build/both, check idempotency." The build_gate outputs `build_analysis_ready_slugs` which contains slugs that passed the build gate. These can have `route == "both"` (startups that are both invest AND build candidates, when `include_both: true` in triage.yaml).

**Verified from triage.yaml line 61:** `include_both: true` — so "both" route slugs ARE included in build_slugs and can reach build gate. [VERIFIED: config/triage.yaml]

**Prevention:** The route check in `deep_research_v2.py` must allow `route in ("build", "both")` — same as `build_research.py` line 155. The plan says this explicitly. Confirm the executor implements it correctly.

### Pitfall 4: `run_deep_analysis` slug discovery — won't find new deep_research.md-only slugs

**What goes wrong:** `run_deep_analysis()` lines 176-180 has a fallback slug discovery path that scans `2_research/` for directories containing `web_research.md` (legacy field). With the new pipeline, slugs may only have `deep_research.md` but no `web_research.md`.

Plan 02-02 Task 2 action says to update this to include `deep_research.md` check. This is **critical** — without it, if `slugs=None` is passed to `run_deep_analysis()`, the fallback scan won't find startups that only have `deep_research.md`. [VERIFIED: deep_analysis.py lines 176-181]

**However:** In the main pipeline flow (`run_pipeline.py`), `run_deep_analysis(slugs=all_analysis_ready)` always passes an explicit slug list. The fallback scan is only used when running `deep_analysis.py` standalone (`if __name__ == "__main__"`). Still, fix it as Plan 02-02 specifies.

### Pitfall 5: `collect_pipeline_stats()` — `researched` count uses legacy `web_research.md`

**What goes wrong:** `digest_generator.py` line 47-50:
```python
researched = len([
    d for d in RESEARCH_DIR.iterdir()
    if d.is_dir() and (d / "web_research.md").exists()
]) if RESEARCH_DIR.exists() else 0
```

After Phase 2, research directories will have `deep_research.md` but NOT `web_research.md` (which was the legacy unified research format). The `researched` count in the Pipeline Summary will show 0 even when startups have been deep-researched.

**Plan 02-03 Task 1 adds `killed_count` to `collect_pipeline_stats()` but does NOT fix the `researched` counter.** This is a gap in the plans.

**Recommendation:** When updating `collect_pipeline_stats()` in Plan 02-03, also update the `researched` count to check for `build_research.md` OR `deep_research.md`:
```python
researched = len([
    d for d in RESEARCH_DIR.iterdir()
    if d.is_dir() and any(
        (d / f).exists()
        for f in ("web_research.md", "build_research.md", "deep_research.md")
    )
]) if RESEARCH_DIR.exists() else 0
```

### Pitfall 6: `build_digest_manually()` fallback — still references `invest_verdict` for sorting

**What goes wrong:** The current `build_digest_manually()` references `invest_verdict`, `invest_total`, and INVEST/WATCH sections extensively. Plan 02-03 Task 1 rewrites this function. If the rewrite is incomplete and any old references remain, the fallback digest will show incorrect sections.

**The LLM path (`generate_digest_with_llm`)** is primary and will use the new prompt — so this only matters when LLM fails (fallback mode). Still, verify the rewrite is complete.

### Pitfall 7: `generate_digest_with_llm` — `analysis_count < 50` threshold

**What goes wrong:** `digest_generator.py` line 314: `if analysis_count < 50:` — the LLM is only called when there are fewer than 50 analysis files. With the current 11 analysis files (and no more expected per run), this always triggers the LLM path. This is correct behavior and will remain correct.

**No issue.** Just note this threshold exists in case future batch runs push over 50.

---

## Recommendations

### R1: Use raw httpx for parallel_client.py (confirmed)

Match the project pattern. Do NOT add `parallel-web` to `requirements.txt`. The httpx approach is 10 fewer lines and zero new dependencies.

### R2: Fix citations extraction (two-level iteration)

The executor for Plan 02-01 Task 1 must implement two-level citation extraction from `output.basis`. See Pitfall 2. This is a runtime correctness issue.

### R3: Fix `collect_pipeline_stats()` researched counter in Plan 02-03

Add `deep_research.md` to the file existence check alongside `web_research.md` and `build_research.md`. Otherwise the Pipeline Summary section will show `Researched: 0`. Low effort, high visibility fix.

### R4: Dry-run Stage 7.5 before full pipeline demo

The 11 build-ready slugs in `2_research/` provide test data. Run `deep_research_v2.py` standalone on 1-2 slugs (`deeptrace`, `lucky`) to verify the Parallel AI API integration before the Thursday demo. This is the highest-risk new component.

### R5: `core` processor is correct for startup research

Do not downgrade to `base`. At $0.025/run × 20 max = $0.50/run, budget is not a constraint. `base` is limited to ~5 output fields and 15-100 seconds — likely insufficient for 6-section research reports.

---

## Code Examples

### Correct httpx client pattern for Parallel AI

```python
# Source: Parallel AI OpenAPI spec (api.parallel.ai/v1/tasks/runs) [VERIFIED]
import httpx, os

BASE_URL = "https://api.parallel.ai/v1"

async def create_task_run(input_text: str, processor: str = "core") -> str:
    api_key = os.getenv("PARALLEL_API_KEY")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/tasks/runs",
            headers={"x-api-key": api_key},  # NOT "Authorization: Bearer ..."
            json={
                "processor": processor,
                "input": input_text,
                "task_spec": {
                    "output_schema": {
                        "type": "text",
                        "description": "Detailed startup research report in Russian with citations"
                    }
                }
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["run"]["run_id"]

async def get_task_result(run_id: str, timeout: int = 600) -> dict:
    api_key = os.getenv("PARALLEL_API_KEY")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/tasks/runs/{run_id}/result",
            headers={"x-api-key": api_key},
            params={"timeout": timeout},
            timeout=timeout + 30,  # httpx timeout must exceed API timeout
        )
        response.raise_for_status()
        return response.json()
```

### Correct citations extraction (two-level)

```python
# output.basis structure: [{field, reasoning, citations: [{url, title, excerpts}], confidence}]
# Source: Parallel AI OpenAPI spec [VERIFIED]
def extract_citations(output: dict) -> list[dict]:
    citations = []
    for basis_item in output.get("basis", []):
        for citation in basis_item.get("citations", []):
            citations.append({
                "url": citation.get("url", ""),
                "title": citation.get("title", ""),
                "excerpt": citation.get("excerpts", [""])[0][:200] if citation.get("excerpts") else "",
            })
    return citations
```

### Semaphore pattern (from build_research.py reference)

```python
# Source: pipeline/build_research.py lines 173-177 [VERIFIED: matches project pattern]
sem = asyncio.Semaphore(3)  # 3 concurrent Parallel AI tasks

async def _throttled(post, slug):
    async with sem:
        return await research_one_deep(post, slug)

tasks = [_throttled(p, s) for p, s in pending]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Build-only frontmatter write (deep_analysis.py update)

```python
# Source: current deep_analysis.py lines 147-156 modified [VERIFIED from source]
# REMOVE invest_total, invest_verdict from frontmatter
analysis_post = frontmatter.Post(
    body,
    name=name,
    url=url,
    build_total=build_total,
    build_verdict=build_verdict,
    analyzed_at=analyzed_at,
    killed=killed,
    kill_reason=kill_reason,
    executive_summary=executive_summary,
    recommended_market=recommended_market,
    time_to_mvp=time_to_mvp,
    time_to_revenue=time_to_revenue,
)
```

### collect_analyses() with new fields and backward-compat .get()

```python
# Source: current digest_generator.py lines 101-114 with additions [VERIFIED from source]
analyses.append({
    "name": post.get("name", slug),
    "url": post.get("url", ""),
    "invest_total": post.get("invest_total", 0),    # keep for backward compat (old files)
    "build_total": post.get("build_total", 0),
    "invest_verdict": post.get("invest_verdict", "PASS"),  # old files only
    "build_verdict": post.get("build_verdict", "SKIP"),
    "category": category,
    "round_raw": round_raw,
    "one_liner": one_liner,
    "content": post.content,
    # NEW fields — absent in old analysis files, safe with .get() defaults:
    "killed": post.get("killed", False),
    "kill_reason": post.get("kill_reason", ""),
    "executive_summary": post.get("executive_summary", ""),
    "recommended_market": post.get("recommended_market", ""),
    "time_to_mvp": post.get("time_to_mvp", ""),
    "time_to_revenue": post.get("time_to_revenue", ""),
})
```

---

## Standard Stack

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| httpx | 0.28.1 (installed) | Parallel AI HTTP calls | Already in requirements.txt |
| python-frontmatter | 1.1+ | Read/write analysis .md files | Already installed |
| asyncio | stdlib | Semaphore, gather, task concurrency | No install needed |
| pyyaml | 6.0+ | Load scoring_weights.yaml | Already installed |

No new dependencies required for the plans as written.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Retry logic for httpx | Custom retry loop | httpx raise_for_status + existing 3-attempt pattern from call_llm |
| Prompt loading | Direct file.read() | `load_prompt("deep_research_brief")` from lib/llm.py |
| Slug-to-idea mapping | New filesystem scan | Pattern from build_research.py lines 138-145 |
| JSON parse with fallback | Try/except everywhere | Pattern from call_llm lines 88-99 |

---

## Common Pitfalls

### Pitfall: httpx timeout for long-running Parallel AI tasks

The `get_task_result` call uses a long `?timeout=600` server-side parameter. The httpx client timeout must be SET HIGHER than the API timeout, or httpx will close the connection before the server responds.

```python
# WRONG:
response = await client.get(url, timeout=30)  # closes connection at 30s

# CORRECT:
response = await client.get(url, timeout=timeout + 30)  # e.g., 630s
```

### Pitfall: deep_research.md written even on API failure

If `run_deep_research_task` catches an exception and returns a fallback dict with `content="(Deep research failed: ...)"`, the module writes this content to `deep_research.md`. On the next run, the idempotency check finds the file and skips. The startup then goes through Stage 8 with empty `deep_research_content`.

**Impact:** Stage 8 analysis will be no better than before Phase 2 for failed slugs. This is acceptable for demo but should be documented as a known limitation.

### Pitfall: `run_deep_analysis` standalone mode still uses old scan

When running `python -m pipeline.deep_analysis` directly (for debugging), the fallback scan at line 178 only checks `web_research.md`. Must update to include `deep_research.md` per Plan 02-02 spec.

---

## Open Questions (RESOLVED)

1. **Does `output.basis` ever have a flat structure instead of nested?**
   - What we know: OpenAPI spec shows nested `citations` inside each `basis_item`
   - What's unclear: Whether the text output schema (`type: "text"`) produces a different `basis` structure than JSON schema outputs
   - **RESOLVED:** Plan 02-01 implements two-level iteration per OpenAPI spec (the safer assumption). Executor MUST log the full `output` dict on the first successful task run to confirm structure. If the structure turns out to be flat in practice, the iteration code degrades gracefully (inner loop yields nothing on missing `citations` key).

2. **Is `category` field available in idea frontmatter for the deep research brief?**
   - What we know: `build_research.py` uses `post.get("category", post.get("sector", "technology"))` [VERIFIED: line 45]
   - What's unclear: Whether `category` is populated after triage for all build-routed startups
   - **RESOLVED:** Use the same fallback pattern in `deep_research_v2.py`: `post.get("category", post.get("sector", "technology"))`. Plan 02-01 Task 2 follows build_research.py reference pattern.

3. **Gemini 2.5 Pro context window for analysis prompt with 8000-char deep_research content**
   - What we know: Gemini 2.5 Pro has 1M token context window [ASSUMED from training knowledge]
   - Risk if wrong: Low — even a 128K context window handles ~14,000 chars of input trivially
   - **RESOLVED:** Non-issue at any reasonable context window size. No action needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| httpx | parallel_client.py | Yes | 0.28.1 | — |
| python-frontmatter | deep_analysis.py, digest_generator.py | Yes | 1.1+ | — |
| PARALLEL_API_KEY | parallel_client.py | Unknown — user must add | — | Stage 7.5 skips gracefully if key absent |
| 2_research/ build data | Stage 7.5 test | Yes | 11 slugs ready | — |

**PARALLEL_API_KEY is the only external dependency that is not yet configured.** The pipeline will fail at Stage 7.5 with a clear error (401 Unauthorized or ValueError if checked at startup). Plans should document this as user setup step.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Gemini 2.5 Pro has 1M token context window | Question 9 analysis | Low — even 128K is fine for this prompt size |
| A2 | `output.basis` structure is nested (basis_items containing citations arrays) for text output schema | Pitfall 2 | HIGH — wrong extraction path causes KeyError |

---

## Sources

### Primary (HIGH confidence)
- docs.parallel.ai/getting-started/pricing — Verified processor pricing per 1,000 runs
- docs.parallel.ai/task-api/guides/choose-a-processor — Verified tier descriptions and timing
- docs.parallel.ai/getting-started/rate-limits — Verified 2,000 RPM limit (POST only)
- docs.parallel.ai/public-openapi.json — Verified API endpoint URLs and response schema
- pypi.org/project/parallel-web — Verified SDK name, version (0.4.2), and interface
- pipeline/deep_analysis.py — Read full source, verified all line references
- pipeline/digest_generator.py — Read full source, verified all line references
- run_pipeline.py — Read full source, verified `build_ready` variable name and position
- pipeline/build_gate.py — Read full source, verified `build_analysis_ready_slugs` return key
- config/triage.yaml — Verified `include_both: true` and pipeline_tracks settings
- .env.example — Verified `OPENROUTER_MODEL_HEAVY=google/gemini-2.5-pro`
- 3_analysis/*.md (11 files) — Verified existing frontmatter field set
- requirements.txt — Verified httpx>=0.27 present, no parallel-web

### Secondary (MEDIUM confidence)
- docs.parallel.ai/public-openapi.json (via WebFetch) — output.basis nested structure described; confirmed as nested citations

---

## Metadata

**Confidence breakdown:**
- Architecture validation (Q1-Q10): HIGH — all verified from source code and official docs
- Pitfall identification: HIGH — sourced from code review, confirmed with line numbers
- Parallel AI API spec: HIGH — official OpenAPI spec fetched
- Processor pricing: HIGH — official pricing page fetched
- Rate limits: HIGH — official rate limits page fetched

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (Parallel AI API is stable, project code doesn't change between sessions)

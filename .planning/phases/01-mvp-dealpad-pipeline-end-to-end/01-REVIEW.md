---
phase: 01-mvp-dealpad-pipeline-end-to-end
reviewed: 2026-04-10T12:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - config/triage.yaml
  - pipeline/triage.py
  - pipeline/research_gate.py
  - pipeline/deep_research.py
  - pipeline/digest_generator.py
  - run_pipeline.py
  - prompts/triage.md
  - prompts/research_gate.md
  - SCHEMA.md
findings:
  critical: 1
  warning: 6
  info: 4
  total: 11
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-10T12:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the 7-stage startup scouting pipeline: triage, research gate, deep research, digest generation, and the orchestrator (`run_pipeline.py`), plus config and prompt files. The codebase is well-structured with clean separation of concerns, idempotent pipeline stages, and graceful LLM failure handling.

Key concerns: a deprecated `datetime.utcnow()` usage, an inline prompt in `deep_research.py` that violates project conventions, unhandled exceptions when `RESEARCH_DIR` does not exist during digest generation, and an efficiency issue where idea files are re-read multiple times in a loop. No hardcoded secrets or injection vulnerabilities were found.

## Critical Issues

### CR-01: Unhandled exception when RESEARCH_DIR does not exist in digest_generator.py

**File:** `pipeline/digest_generator.py:48`
**Issue:** `collect_pipeline_stats()` calls `RESEARCH_DIR.iterdir()` guarded by `RESEARCH_DIR.exists()`, but `collect_analyses()` at line 70 does `ANALYSIS_DIR.glob("*_analysis.md")` without checking if `ANALYSIS_DIR` exists. On a fresh run where `3_analysis/` has not been created yet (e.g., if all startups were filtered at the research gate), `ANALYSIS_DIR.glob()` will silently return an empty iterator on most systems, but this is inconsistent with the rest of the function that does guard directory existence. More critically, `_extract_section()` at line 118-131 is called on `a["content"]` which comes from `post.content`. If `post.content` is `None` (possible with malformed analysis files), `content.split("\n")` will raise `AttributeError: 'NoneType' object has no attribute 'split'`.

**Fix:**
```python
# In collect_analyses(), line 70:
def collect_analyses() -> list[dict]:
    """Read all analysis files and return sorted list of analysis dicts."""
    if not ANALYSIS_DIR.exists():
        return []
    analyses = []

# In _extract_section(), line 119:
def _extract_section(content: str, header: str) -> str:
    """Extract text from a markdown section by header name."""
    if not content:
        return ""
    lines = content.split("\n")
```

## Warnings

### WR-01: Inline prompt in deep_research.py violates project convention

**File:** `pipeline/deep_research.py:39-49`
**Issue:** The project's CLAUDE.md states: "All prompts go in a separate folder -- never hardcode prompts in business logic." The `research_one()` function constructs its LLM prompt inline as an f-string rather than loading it from `prompts/`. Every other pipeline stage (`triage.py`, `research_gate.py`, `deep_analysis.py`, `digest_generator.py`) correctly uses `load_prompt()`. This makes the prompt harder to iterate on and violates the established pattern.

**Fix:** Create `prompts/deep_research.md` with the prompt template using `{name}`, `{url}`, `{round_raw}`, `{description}`, `{website_content}` placeholders, then load and substitute:
```python
from lib.llm import call_llm, load_prompt

# In research_one():
prompt_template = load_prompt("deep_research")
prompt = (
    prompt_template
    .replace("{name}", str(name))
    .replace("{url}", str(url))
    .replace("{round_raw}", str(post.get('round_raw', 'Unknown')))
    .replace("{description}", str(post.content))
    .replace("{website_content}", website_text[:2000])
)
```

### WR-02: datetime.utcnow() is deprecated since Python 3.12

**File:** `pipeline/deep_research.py:34`
**Issue:** `datetime.utcnow()` is deprecated in Python 3.12+ and will be removed in a future version. The same issue exists in `pipeline/deep_analysis.py:97` and `scouts/dealpad_parser.py:198`. Use `datetime.now(datetime.timezone.utc)` instead.

**Fix:**
```python
from datetime import datetime, timezone

# Replace:
datetime.utcnow().isoformat()
# With:
datetime.now(timezone.utc).isoformat()
```

### WR-03: Slug-to-idea lookup in research_gate.py scans all files linearly -- fragile name matching

**File:** `pipeline/research_gate.py:160-166`
**Issue:** The `idea_map` is built by iterating all idea files and computing `make_slug(post.get("name", ""))` as the key. But in `deep_research.py:109`, the slug is computed as `make_slug(post.get("name", idea_file.stem))`, which uses the file stem as fallback. If a startup's `name` field is empty or missing, the slug used as the research directory name will differ from the slug in the `idea_map`, causing a lookup miss. The research gate then creates a minimal stub (`frontmatter.Post("", name=slug, url="")`), losing all original idea metadata. This same fragile pattern exists in `deep_analysis.py:188-196`.

**Fix:** Use the idea file stem (which includes the date prefix and slug) as part of the lookup key, or normalize the slug derivation consistently across all pipeline stages. A helper like `slug_for_idea(post, file_path)` would centralize this logic:
```python
def slug_for_idea(post: frontmatter.Post, file_path: Path) -> str:
    name = post.get("name", "")
    return make_slug(name) if name else make_slug(file_path.stem)
```

### WR-04: triage.py re-reads all idea files for research list assembly

**File:** `pipeline/triage.py:191-200`
**Issue:** After triaging, the function re-reads every idea file via `load_idea()` in a loop to build the research list for previously triaged ideas. This re-reads files that were already loaded and processed earlier in the same function. With a large number of ideas, this doubles the I/O. More importantly, the re-read loop does not check whether the file was already added to `research_list` by the stem check on line 196 -- it checks `file_path.stem in research_list` which is correct, but the double-read is unnecessary.

**Fix:** Build the research list from a single pass over all files, or cache loaded posts:
```python
# Replace lines 191-200 with logic that builds the full research list 
# in the main triage loop, tracking all previously-triaged ideas too:
for file_path in all_files:
    post = load_idea(file_path)
    if post.get("filtered") != "passed":
        continue
    ip = post.get("invest_priority")
    bc = post.get("build_candidate")
    if (ip and ip != "low") or bc:
        slug = file_path.stem
        if slug not in research_set:
            research_list.append(slug)
            research_set.add(slug)
```

### WR-05: deep_research.py fires all LLM + scraping tasks concurrently with no rate limiting

**File:** `pipeline/deep_research.py:145`
**Issue:** `asyncio.gather(*research_tasks)` fires all research tasks concurrently. Each task involves both a website scrape (HTTP request) and an LLM call. While `lib/llm.py` has a semaphore limiting to 5 concurrent LLM calls, there is no limit on concurrent scraping requests in `lib/scraper.py`. With a large shortlist (e.g., 50+ candidates), this could overwhelm target websites or trigger rate limiting / IP blocks. The scraper has no concurrency control.

**Fix:** Add a semaphore to `scrape_website()` or to the research task level:
```python
# In deep_research.py:
RESEARCH_SEMAPHORE = asyncio.Semaphore(10)

async def research_one_throttled(post, slug):
    async with RESEARCH_SEMAPHORE:
        return await research_one(post, slug)
```

### WR-06: digest prompt references "quick-scored" and "shortlisted" stages that no longer exist

**File:** `prompts/digest.md:26-27`
**Issue:** The digest prompt template references pipeline stages "Quick-scored" and "Shortlisted" (lines 26-27), but the pipeline was refactored from quick_score to triage-based flow. The current pipeline has stages: parsed, pre-filtered, triaged, researched, research-gated, deep-analyzed. The manual fallback `build_digest_manually()` in `digest_generator.py` correctly uses the new terminology, but the LLM prompt still references obsolete stages. When the LLM processes this prompt, it will try to report on stages that don't exist in the data, producing a misleading digest.

**Fix:** Update `prompts/digest.md` to match the current 7-stage funnel:
```markdown
- **Parsed:** total startups ingested
- **After pre-filter:** passed niche/size/quality filters
- **Triaged:** received binary evidence assessment (high/medium/low priority)
- **Researched:** website scraped and research notes generated
- **Research-gated:** passed analysis readiness check
- **Deep analyzed:** received full LLM scoring
```

## Info

### IN-01: Unused import `json` in triage.py

**File:** `pipeline/triage.py:2`
**Issue:** `json` is imported but never used in the module.

**Fix:** Remove `import json`.

### IN-02: Duplicated `_coerce_bool()` function across modules

**File:** `pipeline/triage.py:38-44` and `pipeline/research_gate.py:33-39`
**Issue:** The `_coerce_bool()` function is identically implemented in both `triage.py` and `research_gate.py`. This is a minor code duplication. Per project conventions ("Prefer iteration and modularization over code duplication"), this could be extracted to `lib/utils.py`.

**Fix:** Move `_coerce_bool()` to `lib/utils.py` and import from both modules.

### IN-03: Unused import `time` in deep_research.py (partially)

**File:** `pipeline/deep_research.py:4`
**Issue:** `time` is imported and used only for elapsed time tracking in `run_deep_research()`, but `research_one()` does not use it. This is fine, just noting it is used only at the orchestration level.

**Fix:** No action needed -- the import is used, just not in every function.

### IN-04: SCHEMA.md gate.md section is plain markdown, not YAML frontmatter

**File:** `SCHEMA.md:62-76`
**Issue:** The SCHEMA.md documents `gate.md` as having a YAML contract, but the actual `gate.md` written by `research_gate.py` (lines 201-218) is plain markdown with bullet points, not YAML frontmatter. The schema and implementation are inconsistent. If any future consumer tries to parse `gate.md` with frontmatter, it will fail.

**Fix:** Either update `SCHEMA.md` to reflect that `gate.md` is plain markdown (documenting the bullet-point format), or update `research_gate.py` to write `gate.md` with YAML frontmatter as documented.

---

_Reviewed: 2026-04-10T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

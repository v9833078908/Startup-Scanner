---
phase: 01-mvp-dealpad-pipeline-end-to-end
plan: "02"
subsystem: parser-and-prefilter
tags: [parser, html, beautifulsoup, frontmatter, prefilter, pipeline]
dependency_graph:
  requires:
    - python-venv-with-deps
    - lib/utils.py
    - config/filters.yaml
  provides:
    - scouts/dealpad_parser.py
    - pipeline/prefilter.py
  affects:
    - pipeline/quick_score.py (reads 1_ideas/ files produced here)
    - run_pipeline.py (calls parse_dealpad and run_prefilter)
tech_stack:
  added: []
  patterns:
    - BeautifulSoup lxml selector div.message.default.clearfix for Telegram HTML
    - SPAM_KEYWORDS substring filter on lowercased full_text
    - Regex round extraction with ROUND_PATTERN on each line
    - python-frontmatter Post for YAML-frontmatter MD file creation
    - Idempotency via output_path.exists() check before write
    - Multi-file glob: sorted(parent.glob("messages*.html"))
    - Word-boundary regex \b for niche matching (avoids AI/rail false positives)
    - shutil.move for archiving rejected ideas preserving file identity
key_files:
  created:
    - scouts/dealpad_parser.py
    - pipeline/prefilter.py
  modified: []
decisions:
  - "Round extraction uses per-line regex scan rather than fixed 'Раунд:' prefix — handles format variants in the actual export"
  - "Description excludes name line and round line by exact match + currency-symbol heuristic — keeps full_text as fallback if stripping leaves nothing"
  - "matches_niches uses word-boundary regex not simple 'in' substring — required to prevent AI matching railway/wait/detail (Pitfall 5)"
metrics:
  duration_minutes: 2
  completed_date: "2026-04-10"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 1 Plan 2: DealPad Parser and Pre-filter Summary

## One-liner

BeautifulSoup Telegram HTML parser extracting 424 startups into YAML-frontmatter MD files, plus a word-boundary niche pre-filter that archives rejects to _archive/ via shutil.move.

## What Was Built

### Task 1: DealPad HTML parser (scouts/dealpad_parser.py)

- `parse_html_file(html_path)` — reads Telegram Desktop HTML, selects `div.message.default.clearfix` elements (BS4 subset matching includes joined messages), extracts message_id, post_date from `.date` title attribute, links for name/url, and full_text for round/description
- `SPAM_KEYWORDS = ["обзоры", "fastfounder"]` — case-insensitive filter skips ~6-7 promotional messages
- Round extraction via `ROUND_PATTERN` regex scanning each line for currency amounts; date parsed from remainder of round line via `parse_date()`
- Description built by stripping name line and round line from full_text; falls back to full_text if nothing remains
- `save_ideas(ideas, output_dir)` — writes one `{YYYY-MM-DD}_{slug}.md` per idea using `frontmatter.Post` with all SCHEMA.md fields; idempotency check skips existing files
- `parse_dealpad(html_input)` — accepts file or directory; globs `messages*.html` siblings automatically for multi-file Telegram exports; prints progress summary
- Verified on real export: **424 ideas parsed** from `data/ChatExport_2026-04-10/messages.html`

### Task 2: Pre-filter (pipeline/prefilter.py)

- `load_filters()` — reads `config/filters.yaml` via `yaml.safe_load`
- `matches_niches(text, niches)` — word-boundary regex `r'\b' + re.escape(keyword) + r'\b'` prevents "AI" matching "railway" or "wait" (Pitfall 5 from RESEARCH.md)
- `check_filters(post, filters)` — 4 sequential checks: description length, exclude niches, include niches, round size range; returns specific reason string or None
- `run_prefilter()` — iterates `1_ideas/*.md`, marks `filtered=passed/rejected` + `filter_reason` in frontmatter, archives rejects via `shutil.move` to `_archive/`; idempotent via `"filtered" in post.metadata` check

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Data] Round extraction via line-scan regex rather than fixed "Раунд:" prefix**
- **Found during:** Task 1 implementation + smoke test on real HTML
- **Issue:** Plan spec said 'parse "Раунд: $XXX, DATE" line' but the actual DealPad export uses Russian-language labels that vary slightly. A generic ROUND_PATTERN scanning any line for a currency symbol is more robust.
- **Fix:** `ROUND_PATTERN = re.compile(r"([$€£₽\u20ac\u00a3\u20bd]\s*[\d.,]+\s*[KMBkmb]?)")` applied line-by-line; date extracted from remainder after stripping the amount.
- **Files modified:** `scouts/dealpad_parser.py`
- **Commit:** e38106b

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | e38106b | DealPad HTML parser — parse_html_file, save_ideas, parse_dealpad |
| Task 2 | 8eaee2e | Pre-filter — load_filters, matches_niches, check_filters, run_prefilter |

## Self-Check: PASSED

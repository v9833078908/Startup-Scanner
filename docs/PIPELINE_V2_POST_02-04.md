# Pipeline V2 — logic after 02-04 (for reviewer context)

> Self-contained description of how data flows through the scouting pipeline after plan 02-04 lands. Written for an independent code reviewer who needs to evaluate 02-04 without reading the full `.planning/` tree.

## Overall shape

10 stages, BUILD-only funnel (Phase 2). Single startup path:
`1_ideas/ → 2_research/{slug}/ → 3_analysis/{slug}.md → digests/`.

## Stages

| # | Stage | Code | Input | Output |
|---|---|---|---|---|
| 1 | Parse DealPad | `run_pipeline.py` | HTML export | `1_ideas/{date}_{slug}.md` (~424 files per batch) |
| 2 | Pre-filter | `pipeline/prefilter.py` | ideas | ideas with `prefilter_verdict` (light LLM) |
| 3 | Triage | `pipeline/triage.py` | prefiltered | ideas with `route: build\|skip`, `build_thesis` (light LLM) |
| 4 | Invest research | — | — | **SKIPPED** (Phase 2 is build-only) |
| 5 | Build research | `pipeline/build_research.py` | ideas with `route=build` | `2_research/{slug}/build_research_raw.json` (raw bucket results from Exa/DDG, ~70KB) + `build_research.md` (LLM synthesis, ~3KB, light model) |
| 6 | Invest gate | — | — | **SKIPPED** |
| 7 | Build gate | `pipeline/build_gate.py` | `build_research.md` | `gate_build.md`: 5 boolean signals + `build_analysis_ready: bool` (medium LLM) |
| 8 | Deep research v2 | `pipeline/deep_research_v2.py` | gate-passed slugs | `2_research/{slug}/deep_research.md` with citations (Parallel AI Task API, heavy model) |
| 9 | Deep analysis | `pipeline/deep_analysis.py` | `deep_research.md` + gate | `3_analysis/{slug}.md` with `killed: bool`, `kill_reason`, `executive_summary`, `build_verdict ∈ {BUILD,PARTNER,MONITOR,SKIP}`, `build_score` (Gemini 2.5 Pro, heavy) |
| 10 | Digest | `pipeline/digest_generator.py` | `3_analysis/*.md` | `digests/{date}_daily.md` — Python deterministically copies `executive_summary` per startup; LLM only narrows to `key_findings + trends` JSON |

### Folder semantics (from `CLAUDE.md`)

- `1_ideas/` — raw findings from parsers (markdown files)
- `2_research/{slug}/` — enriched data per startup (folder of multiple `.md` files + sidecar JSON). All *research* artifacts live here (facts, evidence, intermediate LLM interpretations).
- `3_analysis/{slug}.md` — one file per startup with *verdict + scoring + conclusions*. Not facts; decisions.

## What 02-04 changes

**No new stage is added.** 02-04 enriches the **inputs** of two existing stages (8 and 9) with additional context that already sits on disk but was previously ignored.

### Stage 8 enrichment (Parallel AI deep research)

Before 02-04: Parallel AI receives only `{name, url, description, round_raw, category, build_thesis}` — ~2KB of triage-level data.

After 02-04: `_build_brief` in `pipeline/deep_research_v2.py` substitutes 4 new blocks into the prompt. All reads are graceful (missing → placeholder, never raises):

1. **`{raw_evidence}` (PRIMARY)** — `_format_raw_evidence(2_research/{slug}/build_research_raw.json)` → raw bucket results (5 buckets × ~5 URLs + title + snippet[:200]), capped at 6000 chars. Independent data points: URLs are real, Parallel AI can follow them.
2. **`{preliminary_findings}` (SECONDARY)** — `2_research/{slug}/build_research.md[:3000]` → LLM synthesis of the same raw evidence produced by a cheap model. Explicitly framed as *"cheap-LLM interpretation, may be wrong"*.
3. **`{gate_signals}`** — `_format_gate_signals(gate_build.md)` → 5 signal lines + Decision. Framed as *"interpretation, not facts"*.
4. **`{website_summary}`** — `website.md[:2000]` → landing page content (if present).

**Section ordering in the prompt is intentional**: raw evidence on top, LLM summary below. Closing rule: *"Source of truth for your final answer is your own independent research. The blocks above are inputs to VALIDATE/REFUTE/EXTEND, not conclusions to confirm."*

**Why this ordering matters.** The naive "feed-the-digest" approach (summary only) anchors Parallel AI on the cheap DDG+LLM layer's mistakes. Feeding raw first + summary as a hint lets the model form an independent opinion before it sees our interpretation.

Token budget: ~14,000 chars total (well under Parallel AI's 25,000 limit).

### Stage 9 enrichment (deep_analysis)

Before 02-04: Stage 9 reads `deep_research.md` + `website.md` + a bundle of research notes.

After 02-04: a single new `{gate_signals}` variable is substituted into the prompt. The helper is imported from `lib.research_utils` (**not** from `pipeline.deep_research_v2`). The prompt explicitly states:

> *"Source of truth for the verdict = `deep_research.md`. Gate signals are SECONDARY. On conflict, trust deep_research and note the discrepancy in `executive_summary`. Use gate as an extra hypothesis for kill-signal detection."*

**Why.** Gate signals help deterministically trigger `killed=True, kill_reason="рынок занят"` when `cis_gap_confirmed=False` + `market_demand_signals=True` — stronger than relying solely on the deep_research narrative.

## Architectural boundary

A new module `lib/research_utils.py` (stdlib-only) contains two pure functions:

- `_format_gate_signals(gate_path) → str` — parses `gate_build.md` into a human-readable block
- `_format_raw_evidence(raw_path, max_chars=6000) → str` — compacts `build_research_raw.json` into a prompt-friendly format

**Both pipeline modules import from `lib/`, never from each other.** Rule: `lib/` can be a dependency of `pipeline/`, but not the reverse. Cross-pipeline import is explicitly forbidden and enforced by an assertion in the verification block.

## Graceful degradation

Each of the 4 new file reads can fail in four ways: file not found, read error, malformed JSON, empty buckets. All four return a documented placeholder string (`"(Stage 5 raw evidence not available — malformed JSON)"` etc.). **The pipeline never blocks on one bad startup** — project philosophy (`CLAUDE.md`).

## `3_analysis/{slug}.md` frontmatter (shipped 02-02 — critical for reviewer)

```yaml
killed: bool
kill_reason: str | null
executive_summary: str       # ← copied byte-for-byte into digest (02-03)
build_verdict: BUILD|PARTNER|MONITOR|SKIP   # 4 values, no PASS/WATCH
build_score: float
```

**Critical:** `executive_summary` is the single "quality lever" for the digest (because 02-03 copies it verbatim). All digest quality gains must come through improving Stage 8 and Stage 9 inputs — which is precisely what 02-04 does.

## Why `deep_research.md` stays in `2_research/{slug}/` (not `3_analysis/`)

- **Semantics**: research = facts we gathered; analysis = decisions we made. `deep_research.md` has citations and no verdict — it is facts with interpretation, not a decision.
- **Symmetry**: sits next to other research artifacts (`build_research.md`, `gate_build.md`, `website.md`, `build_research_raw.json`) — one folder per startup.
- **Stage 9 convenience**: `analyze_one` already reads `research_dir = 2_research/{slug}/` and pulls all research files from one directory. Splitting across folders would mean two read paths.
- **Versioning**: if a startup is re-researched (new Parallel AI run), the full research history belongs in one folder.

## Where a reviewer should look critically

1. **Section ordering in the Stage 8 prompt** — does `raw_evidence` physically precede `preliminary_findings` in the rendered brief, or will the LLM blur them into one block regardless?
2. **`max_chars=6000` for `raw_evidence`** — is this enough to give Parallel AI material across all 5 buckets × 5 results? Or too aggressive a truncation?
3. **Anti-anchoring tokens** in the prompt (VALIDATE/REFUTE/EXTEND/CHALLENGE + "NOT authoritative" + "source of truth") — do they turn into noise the model ignores?
4. **Graceful placeholder strings** — they are structurally distinguishable (parentheses + "not available"), but still enter the model's context. Is there a risk the model reads `"(Stage 7 gate signals not available)"` and continues it as a fact?
5. **Cross-module imports** — `from lib.research_utils import _format_gate_signals` in both `pipeline/` modules. Any risk of circular dependency on future changes?
6. **Kill-signal detection reliability** — is `gate_signals` in the Stage 9 prompt really enough to reliably trigger `killed=True, kill_reason="рынок занят"`, or does that need an explicit deterministic rule in Python?
7. **Token budget math** — ~14KB for the brief, Parallel AI accepts 25KB. Is the 11KB headroom sufficient given that `description` and `build_thesis` can be longer than estimated?
8. **Fixture independence of smoke tests** — the verification block deliberately avoids entity-name assertions (`Mastra`, `Нейро42`, `gogs/gogs`) because fixtures refresh over time. Structural checks (`===` bucket headers, 5 signal lines + Decision, no leaked `{variable}` placeholders, section ordering) should be verifiable against any future slug in `2_research/`.
9. **Anti-anchoring architecture end-to-end** — the chain of "source of truth" rules is:
   - Stage 7.5 (Parallel AI): your independent research is source of truth
   - Stage 8 (deep_analysis): `deep_research.md` is source of truth, gate is secondary
   - Stage 9 (digest): `executive_summary` from `3_analysis/{slug}.md` is source of truth, byte-for-byte copy

   Is this chain coherent? Does it avoid any circular dependency (e.g., Stage 8 passing gate signals that were themselves derived from Stage 5 LLM synthesis, which the prompt tells the model to distrust)?

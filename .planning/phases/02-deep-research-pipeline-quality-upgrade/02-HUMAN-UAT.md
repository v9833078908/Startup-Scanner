---
status: partial
phase: 02-deep-research-pipeline-quality-upgrade
source: [02-VERIFICATION.md]
started: 2026-04-14T00:00:00Z
updated: 2026-04-14T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end live pipeline run with real PARALLEL_API_KEY + OPENROUTER_API_KEY
expected: `python run_pipeline.py --html <dealpad_export.html>` completes all 10 stages; `2_research/{slug}/deep_research.md` files contain substantive (>500 chars) Russian content with `## Источники` sections (not "(Deep research failed:" stubs); `3_analysis/{slug}_analysis.md` files have non-empty executive_summary, build_verdict ∈ {BUILD,PARTNER,MONITOR,SKIP}; `digests/{YYYY}-W{WW}_weekly.md` is management-ready with byte-for-byte executive_summary insertion.
result: [pending]

### 2. Honest invest guard live trigger
expected: Set `pipeline_tracks.invest=true` in `config/triage.yaml`, run pipeline with a dealpad export that produces at least one invest-routed startup passing invest gate. Pipeline must raise SystemExit with "Phase 2 build-only deep_analysis cannot run with invest track enabled" message. Restore config after test.
result: [pending]

### 3. Digest content quality (Dina's requirement)
expected: Generated digest is readable by non-technical management; executive summaries cover Суть/Рынок/Что строить/Целевой рынок/Time to market/Ключевые риски/Вердикт per startup; no numeric scoring leaked; PASS via kill signals section lists killed startups with meaningful kill_reason.
result: [pending]

### 4. Anti-anchoring effect on Parallel AI output
expected: Compare Parallel AI `deep_research.md` content against preliminary Stage 5 `build_research.md`: Parallel AI should VALIDATE/REFUTE/EXTEND the preliminary findings with independent citations, not merely paraphrase. Spot-check on 2-3 slugs.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

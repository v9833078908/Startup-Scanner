# Startup Scanner — Analysis & Improvement Plan

**Date:** 2026-04-13
**Codebase:** 3324 lines Python, 11 plans executed, 9-stage dual-track pipeline

---

## 1. Current State

```
424 DealPad ideas
├── 178 archived (hard reject)
├── 327 in 1_ideas/ (classified + triaged)
│   ├── Route: invest=145, build=26, both=33, skip=103
│   ├── 18 researched in 2_research/
│   ├── 11 analyzed in 3_analysis/
│   └── 1 digest
```

Pipeline: parse → prefilter → triage → invest/build research (web search) → invest/build gate → deep analysis → digest

**Cost per full run:** ~$3.10 (Flash) + analysis on Pro. ~1457 LLM calls, 3.1M tokens, 45 min.

---

## 2. Architecture Problems (Priority Order)

### P1: invest_*/build_* code duplication (~400 lines)

`invest_research.py` и `build_research.py` — 90% одинаковые. То же для gate модулей. Баги надо фиксить в 4 местах.

**Fix:** Один `track_research.py` с параметром `track_type="invest"|"build"` + config-driven queries. То же для gates. Сократит ~800 строк до ~400.

### P1: Data flow inconsistency

Новые модули пишут `invest_research.md`/`build_research.md`, но `deep_analysis.py:58` и `digest_generator.py:49` читают `web_research.md` (legacy). Deep analysis на новых данных не работает.

**Fix:** Обновить deep_analysis и digest чтобы читали `invest_research.md`/`build_research.md` по route.

### P1: JSON parse → garbage silently written

`llm.py:98` возвращает raw string при JSON failure → `invest_research.py:91` пишет его как markdown. Gates/analysis получают мусор.

**Fix:** `llm.py` должен возвращать `None` при persistent JSON failure, не raw string.

### P2: Semaphore duplication

`llm.py:21` имеет global semaphore=5, но research модули создают свои собственные. При обоих треках = 10 concurrent requests.

**Fix:** Убрать локальные semaphores, использовать глобальный из `llm.py`.

### P2: Config sprawl

`config/triage.yaml` — 64 строки с triage, gates, и pipeline config. Трудно менять.

**Fix:** Разделить на `config/triage.yaml`, `config/gates.yaml`, `config/pipeline.yaml`.

### P3: No tests for core logic

Только `tests/test_web_search.py` (65 тестов). Нет тестов для `compute_route()`, `compute_build_candidate()`, `compute_invest_priority()`, `compute_build_ready()`, weighted scoring.

**Fix:** Unit tests для routing/gating/scoring логики с mock LLM.

### P3: Legacy dead code

`deep_research.py` и `research_gate.py` импортируются в `run_pipeline.py:19-20` но не вызываются.

**Fix:** Удалить или переместить в `_archive/`.

### P5: `_coerce_bool()` и `format_search_results()` дублируются в 3-4 файлах

**Fix:** Вынести в `lib/utils.py`.

---

## 3. Optimization Opportunities

### Incremental pipeline (highest ROI)

Сейчас: re-process all 424 every run. Новых ~50-70 за батч.
**Fix:** Track processed IDs (name+url hash). Triage/research/analysis только новых.
**Impact:** ~$1/run savings, 70% faster.

### Prompt compression (low effort)

Triage prompt 900 tokens → можно сократить до 630 без потери качества. Убрать redundant examples, compact calibration.
**Impact:** ~$0.18/run, ~25% faster triage.

### Product evidence prompt tightening

51% получают `has_product_evidence=True` — LLM принимает feature descriptions за evidence. Нужен stricter prompt: evidence = ТОЛЬКО числа (users, revenue, customers), не описание что продукт делает.

### Build candidate false positive: `cis_gap_likelihood`

Не проверяли accuracy. LLM может отвечать True слишком часто (как было с cis_transferable в Run 2). Нужен audit sample.

---

## 4. Feature Gaps (vs Commercial Tools)

| Feature | Harmonic/Affinity | This Project | Gap |
|---------|-------------------|--------------|-----|
| Multi-source scouting | 30M+ companies | 1 source (DealPad) | Phases 2-3 в roadmap |
| Founder tracking | LinkedIn + hiring signals | None | Phase 3+ |
| CRM integration | Native (Salesforce, HubSpot) | None | Not planned |
| Real-time alerts | Push notifications | None | Phase 6 (Telegram bot) |
| Historical deal data | 10+ years | 1 batch (April 2026) | Incremental accumulation |
| Team/hiring signals | LinkedIn API | None | Phase 4 |
| Deduplication | ML-based | Jaro-Winkler >0.85 | OK for MVP |

**Unique advantages:**
- Dual-track invest/build — no commercial tool does this
- File-based, git-versioned — full audit trail
- LLM-powered scoring — customizable, not black box
- Cost: ~$3/run vs $24K/year (Affinity) or $100K+ (PitchBook)

---

## 5. Roadmap Assessment

| Phase | ROADMAP Status | Reality | Recommendation |
|-------|---------------|---------|----------------|
| 1: MVP Pipeline | 11/11 plans done | Works but has P1 bugs above | Fix P1 bugs before Phase 2 |
| 2: Scout Framework + 6 Parsers | Not started | Blocked by Phase 1 | Start after P1 fixes |
| 3: Auth Parsers (Reddit, PH, TG) | Not started | Blocked by Phase 2 | OK |
| 4: Research Enrichment | Not started | Blocked by Phase 2 | Merge with Phase 1 dual-track |
| 5: Full Scoring Suite | Not started | Blocked by Phase 4 | deep_analysis already covers this |
| 6: Delivery (Telegram, email) | Not started | Blocked by Phase 5 | Most valuable for demo |
| 7: Advanced Features | Not started | Blocked by Phase 3 | Low priority |

**Key insight:** Phase 4 (Research Enrichment) is partially done — invest/build research modules already exist. Phase 5 (Full Scoring) is mostly done — deep_analysis with weighted scoring exists. The roadmap is outdated.

---

## 6. Recommended Next Steps (Priority Order)

### Immediate (before next pipeline run)

1. **Fix P1 data flow bug** — deep_analysis reads wrong research files
2. **Fix JSON garbage writes** — llm.py should return None on parse failure
3. **Audit cis_gap_likelihood accuracy** — sample 10 ideas, check manually

### Short-term (this week)

4. **Merge invest_*/build_* into parameterized modules** — cut 400 lines of duplication
5. **Add incremental processing** — skip already-triaged ideas on re-runs
6. **Tighten product evidence prompt** — 51% → target 20-30%
7. **Unit tests for routing/gating logic** — pure functions, easy to test

### Medium-term (next milestone)

8. **Add 3-5 easy parsers** (GitHub Trending, HN, RSS) — breadth of sources
9. **Telegram digest delivery** — most valuable for demo (April 15)
10. **Update roadmap** — reflect what's already built in Phase 1

### Research to validate

11. **Batch triage** — 5-10 startups per LLM call for pre-classification (test quality)
12. **SSFF framework** — published ML approach to startup scoring (GitHub: xisen-w/Startup-Success-Forecasting-Framework)
13. **Harmonic-style signals** — hiring activity + founder movement as scoring inputs

---

## 7. Cost Model

| Scenario | LLM Calls | Tokens | Cost | Time |
|----------|-----------|--------|------|------|
| Current (all 424, both tracks) | ~1457 | 3.1M | ~$3.10 | 45 min |
| Build-only (59 startups) | ~400 | ~800K | ~$0.80 | 12 min |
| Incremental (70 new) | ~350 | ~700K | ~$0.70 | 10 min |
| With prompt compression | ~350 | ~500K | ~$0.50 | 8 min |

**Annual cost (weekly runs):** $26-$160 depending on mode. Negligible vs $24K Affinity.

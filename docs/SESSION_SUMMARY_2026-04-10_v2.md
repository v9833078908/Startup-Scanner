# Session Summary v2 — 2026-04-10

## What Was Done

### Plan 01-07: 5-Stage Triage Funnel (executed)
- `pipeline/triage.py` — binary evidence signals (has_product_evidence, has_founder_signal)
- `pipeline/research_gate.py` — Stage 4.5, rare build signal detection + analysis readiness
- Deleted: `quick_score.py`, `scoring_formula.yaml`, `quick_score.md`
- Pipeline: 7 stages, `--reset` updated

### Plans 01-08..10: Invest/Build Track Split (executed)
- **01-08**: Triage extended with build signals (replicability, cis_gap_likelihood, stack_fit) + `route` field (invest/build/both/skip) + tighter `build_candidate`
- **01-09**: `lib/exa_client.py` + 4 pipeline modules (invest_research, build_research, invest_gate, build_gate) + 4 prompts
- **01-10**: `run_pipeline.py` → 9-stage dual-track pipeline fork

### Bug Fixed
`triage.py` slug mismatch: used `file_path.stem` (with date prefix) instead of `make_slug(name)` → deep_research couldn't match slugs → 0 researched. Fixed to use `make_slug()`.

## Pipeline Runs Comparison

| Metric | Run 2 (01-06) | Run 3 (01-07) | Run 4 (01-08 triage only) |
|--------|---------------|---------------|--------------------------|
| Parsed | 424 | 424 | 424 |
| Hard rejected | 118 | 94 | 94 |
| Classified | 306 | 307 | 307 |
| build_candidate | 191 (63%) | 238 (78%) | **59 (19%)** |
| Research list | 191 | 271 | **204** |
| Route: invest | — | — | 145 |
| Route: build | — | — | 26 |
| Route: both | — | — | 33 |
| Route: skip | — | — | **103** |

### Run 3 Full Results (01-07, 7-stage)
- 424 → 94 reject → 307 triage → 271 research → 206 gate → 206 analyzed
- 1 INVEST, 174 WATCH, 31 PASS
- 4 BUILD, 191 PARTNER (95% — inflated)
- 1457 LLM calls, 3.1M tokens, 45 min

### Key Findings
1. **Founder signal calibration works**: 0.6% (was ~10%) — LLM honest about missing data
2. **Product evidence still inflated**: 51% — LLM treats feature descriptions as evidence
3. **Research gate too permissive**: 76% pass — traction(90%) + competitive(72%) hallucinated from training data
4. **Build score inflated**: 95% BUILD/PARTNER — same B2B software inflation
5. **Root cause**: `web_research.md` from LLM training data, not real web search → need Exa

### Run 4 Triage Improvements
- build_candidate: 78% → **19%** (replicability + stack_fit filter works)
- Route-based skip: **103 startups** won't waste Exa credits
- Build-only: 26 → ~78 Exa queries (3 per startup)
- Invest-only: 145 → ~290 Exa queries (2 per startup)
- Both: 33 → ~165 Exa queries (5 per startup)
- **Total Exa: ~533** (fits in 1000 free tier)

## Build-Only Candidates (26) — For Manual Review

| # | Name | Repl. | Category | Round | One-liner |
|---|------|-------|----------|-------|-----------|
| 1 | GetWhys | medium | general AI | $4.80M | ИИ обученный на личном опыте |
| 2 | Riplo | medium | AI consulting | $3.04M | Agentic OS для консалтинга |
| 3 | Sett | medium | AI ad creative | $30M | ИИ для создания видео-рекламы в масштабе |
| 4 | Aiphoria | medium | AI HR tech | $40M | AI-сотрудники для операционной эффективности |
| 5 | Allegro Finance | medium | fintech | $2.65M | Финтех без деталей |
| 6 | Enclave | medium | AI code security | $6M | AI-агент для безопасности кода |
| 7 | Rowan | medium | succession planning | $3.30M | Планирование преемственности для малого бизнеса |
| 8 | Alien | medium | AI human verification | $7.10M | Доказательство человечности в эпоху ИИ |
| 9 | Armored Things | medium | proptech | $11.53M | Планирование пространства на данных |
| 10 | Kalamata Capital | medium | fintech MCA | $111.87M | Авансы под торговую выручку |
| 11 | Lemay.ai | easy | AI/ML consulting | $2.59M | AI/ML консалтинг и цифровая трансформация |
| 12 | Sona | medium | HR workforce mgmt | $45M | Платформа управления персоналом |
| 13 | Miravoice | medium | AI surveys | $6.30M | Автоматизированные телефонные опросы |
| 14 | SYSLEA | medium | AI SaaS work | $2.57M | AI SaaS для стилей работы |
| 15 | AI6 Technologies | medium | AI/ML | $4.61M | AI/ML без деталей |
| 16 | Genspark AI | medium | general AI/ML | $385M | AI без деталей |
| 17 | Moonbounce | medium | AI policy enforcement | $12M | Контроль безопасности и политик |
| 18 | Pixie Chess | easy | gamedev chess | $5.20M | Шахматная игровая студия |
| 19 | Deeptrace | medium | AI ops automation | $5M | Автоматизация отладки с ИИ |
| 20 | Lucky | medium | fintech rewards | $23M | Бесплатные деньги при покупках (Египет) |
| 21 | Monetary Metals | easy | fintech | $2.07M | Финтех без описания |
| 22 | Natter | medium | analytics insights | $23M | Сбор пользовательских инсайтов в масштабе |
| 23 | Ricerca | medium | AI operations | $10.73M | GenAI для приема и размещения заказов |
| 24 | Zanskar Securities | medium | fintech | $2.71M | Финтех без деталей |
| 25 | Atlas | medium | AI ops infrastructure | $6M | AI-системы для обслуживания клиентов |
| 26 | Golden Analytics | medium | analytics | $7M | Аналитика без деталей |

## Both-Track Candidates (33) — Invest + Build

Top picks by category:
- **AI HR/coaching**: Aiphoria, Sona, Asendia AI, Dehurdle
- **Fintech**: Bachatt, AccuQuant, GoSats, Alloy
- **Devtools/AI**: Ridge AI, nFuse.ai, Fastrflow
- **B2B SaaS**: Lobby, Sahor One, Grapple, OnSite
- **Gamedev**: Pixie Chess (build-only), Cave Duck (both)

## Architecture After Plans 01-08..10

```
parse → prefilter → triage ─┬─ invest (145) → invest_research (Exa) → invest_gate → analysis
                             ├─ build (26)   → build_research (Exa)  → build_gate  → analysis
                             ├─ both (33)    → both tracks
                             └─ skip (103)   → no research
```

Pipeline: 9 stages. Exa API for real web search (not LLM training data).

## Pending

1. **Add EXA_API_KEY to .env** — get key from exa.ai
2. **Run full 9-stage pipeline** — verify Exa integration works
3. **Tighten product evidence prompt** — 51% still inflated, needs stricter wording
4. **Commit triage.py fix** — route/replicability/stack_fit code was lost during cherry-pick, re-applied manually

## Files Structure (updated)

```
config/triage.yaml              — triage thresholds + route rules + build gate config
prompts/triage.md               — 8-question triage prompt (5 invest + 3 build)
prompts/invest_research.md      — Exa invest research synthesis prompt
prompts/build_research.md       — Exa build research synthesis prompt
prompts/invest_gate.md          — invest evidence gate prompt
prompts/build_gate.md           — build readiness gate prompt
lib/exa_client.py               — Exa SDK wrapper (exa_search)
pipeline/triage.py              — triage with route computation
pipeline/invest_research.py     — Exa-powered invest research
pipeline/build_research.py      — Exa-powered build research
pipeline/invest_gate.py         — invest evidence gate (2/3 threshold)
pipeline/build_gate.py          — build readiness gate (CIS gap OR replicable+demand)
pipeline/deep_research.py       — legacy unified research (kept as fallback)
pipeline/research_gate.py       — legacy unified gate (kept as fallback)
run_pipeline.py                 — 9-stage dual-track pipeline orchestrator
```

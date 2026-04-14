# Roadmap — Startup Scouting Pipeline

## Milestone 1: Scouting Pipeline v1.0

### Phase 1: MVP — DealPad Pipeline End-to-End (COMPLETE)
- **Goal:** Working 9-stage dual-track pipeline: DealPad HTML → triage with invest/build routing → web search research → gates → analysis → digest
- **Status:** Complete (11 plans executed)
- **Plans:** 11/11 complete

Plans:
- [x] 01-01 — Project setup, config, shared libs, prompts
- [x] 01-02 — DealPad HTML parser + pre-filter
- [x] 01-03 — LLM quick scoring (replaced in 01-07)
- [x] 01-04 — Deep research + deep analysis
- [x] 01-05 — Digest generator + pipeline orchestrator
- [x] 01-06 — LLM classification pre-filter + formula scoring
- [x] 01-07 — 5-stage triage funnel (binary signals + research gate)
- [x] 01-08 — Triage build signals (replicability, stack_fit, route)
- [x] 01-09 — Exa client + dual research + dual gates
- [x] 01-10 — 9-stage dual-track pipeline wiring
- [x] 01-11 — Web search abstraction (DDG/Exa/Sonar)

### Phase 2: Deep Research + Pipeline Quality Upgrade (BUILD-ONLY)
- **Goal:** Add Deep Research stage (7.5) via Parallel AI Task API, upgrade Deep Analysis (Stage 8) with kill signals + executive summaries, upgrade Digest (Stage 9) for informative management-ready output
- **Depends on:** Phase 1
- **Context:** Meeting 2026-04-13 — Дина: текущая выдача "пустые звуки", катастрофически мало информации для управленческих решений. Нужны executive summaries по каждому стартапу, суть бизнеса, TAM, конкуренты, time to market. Убрать числовой скоринг из дайджеста. Бюджет: ~$50/нед на платные API.
- **TEMPORARY LIMITATION:** Phase 2 deep_analysis is BUILD-ONLY. Invest deep analysis is not supported — `pipeline_tracks.invest=true` will trigger SystemExit at the deep_analysis step. Reason: anchoring bias when invest+build scoring share an LLM context. Invest mode will return in a future phase as a separate prompt + LLM call.
- **Verdict Taxonomy (canonical):** `build_verdict ∈ {BUILD, PARTNER, MONITOR, SKIP}` (4 values, no PASS, no WATCH). Killed startups use a separate `killed: bool` + `kill_reason: str` flag — verdict label is never overloaded.
- **Success Criteria:**
  - [ ] `lib/parallel_client.py` — async client for Parallel AI Task API (create task, poll result)
  - [ ] `pipeline/deep_research_v2.py` — Stage 7.5: deep research for gate-passed startups via Parallel AI (canonical name with `_v2` suffix; legacy `deep_research.py` kept for backward compat until Phase 4 cleanup)
  - [ ] `prompts/deep_research_brief.md` — research brief prompt (суть бизнеса, TAM, конкуренты, traction, build assessment, география)
  - [ ] Output: `2_research/{slug}/deep_research.md` with citations
  - [ ] Updated `pipeline/deep_analysis.py` — BUILD-ONLY: reads deep_research.md, kill signals, executive summary, no invest scoring
  - [ ] Updated `prompts/deep_analysis.md` — kill signals (рынок занят, высокий капитал, далеко от компетенций, >6мес до выручки) + executive summary format + build-only scoring
  - [ ] Updated `config/scoring_weights.yaml` — build mode criteria aligned with new doc; invest_mode untouched (preserved for future)
  - [ ] Updated `pipeline/digest_generator.py` — DETERMINISTIC-FIRST: Python composes per-startup sections (BUILD/MONITOR/PASS) with byte-for-byte executive_summary insertion; LLM only for narrow Key Findings + Trends synthesis
  - [ ] Updated `prompts/digest.md` — narrow scope: outputs only `{key_findings, trends}` JSON
  - [ ] Updated `run_pipeline.py` — Stage 7.5 wiring + honest invest guard (SystemExit if invest enabled)
  - [ ] `PARALLEL_API_KEY` env var documented
  - [ ] Full pipeline run produces informative digest for management
- **Plans:** 4 plans

Plans:
- [x] 02-01-PLAN.md — Parallel AI client + Stage 7.5 Deep Research module
- [x] 02-02-PLAN.md — Deep Analysis upgrade (kill signals + executive summaries)
- [x] 02-03-PLAN.md — Digest upgrade + pipeline wiring
- [x] 02-04-PLAN.md — Context enrichment: Parallel AI input + Stage 8 gate_signals

### Phase 3: Multi-Source + Delivery
- **Goal:** Broad source coverage (8-10 parsers) + Telegram digest delivery for daily use
- **Depends on:** Phase 1
- **Requirements:** R9-R15, R22, R24
- **Success Criteria:**
  - [ ] BaseScout class + core/idea_store.py + core/dedup.py
  - [ ] 5+ simple parsers: GitHub Trending, HN, RSS (TechCrunch, Sifted), vc.ru, Betalist
  - [ ] 2-3 auth parsers: ProductHunt, Reddit, Telegram channels
  - [ ] All parsers refactored to BaseScout pattern
  - [ ] Multi-source deduplication with Jaro-Winkler >0.85
  - [ ] Telegram bot: /digest, /top, /build, /status commands
  - [ ] Cron: parsers 3x/day, digest every morning
  - [ ] 50+ ideas per full multi-source run
- **Plans:** 0/0
- **Notes (учесть при планировании):**
  1. **Нормализация неструктурированных источников.** DealPad даёт готовые поля (имя, раунд, ссылка). RSS-статьи, Telegram-сообщения, Reddit-посты — сырой текст. Нужен этап извлечения: regex-шаблоны для типовых форматов + LLM-extraction как fallback. Решить до написания парсеров.
  2. **Конфликт данных при мульти-источниках.** Один стартап на 3 источниках с разным описанием/раундом — кто "прав"? Текущий dedup просто пропускает дубли (первый записавший побеждает). Нужна стратегия enrichment: дополнять существующий файл данными из новых источников, а не игнорировать.
  3. **Пустые поля — норма.** GitHub-стартап без раунда, HN без описания компании — допустимо. Pipeline должен корректно работать с null/empty в round_raw, round_usd, round_date. Проверить что prefilter и triage не ломаются на таких данных.

### Phase 4: Research Quality + Architecture
- **Goal:** Real web search research (not LLM hallucination), clean architecture, incremental processing
- **Depends on:** Phase 1 (can run parallel with Phase 3)
- **Requirements:** R16-R17, R18-R19
- **Success Criteria:**
  - [ ] Merge invest_*/build_* into parameterized track modules (track_research.py, track_gate.py — pipeline_tracks config already controls tracks, but Python code still duplicated)
  - [ ] Verify web search quality across backends (DDG/Exa/Sonar via lib/web_search.py abstraction)
  - [ ] GitHub API enrichment (stars, forks, contributors, commit activity)
  - [ ] Incremental pipeline: process only new ideas since last run
  - [ ] Prompt versioning + cost tracking per run
  - [ ] Unit tests for routing/gating/scoring pure functions
  - [ ] core/ abstraction layer (idea_store, research_store, analysis_store)
  - [ ] Cleanup legacy `pipeline/research_gate.py` + `prompts/research_gate.md` (unused since Phase 01-09 split into invest_gate/build_gate). Rename `research_gate:` section in `config/triage.yaml` → `invest_gate:` and update reference in `pipeline/invest_gate.py:96`.
- **Plans:** 0/0

### Phase 5: Production Polish
- **Goal:** Noise filtering, advanced features, documentation, demo readiness
- **Depends on:** Phase 3 + Phase 4
- **Requirements:** R20-R21, R25-R27
- **Success Criteria:**
  - [ ] Fake traction detection (stars spike, stars:forks >50:1)
  - [ ] "Amateur startup" auto-skip (>3 red flags)
  - [ ] Daily + weekly + monthly digest variants
  - [ ] Build opportunities report (monthly, ranked)
  - [ ] YC Lookalike search
  - [ ] Founder tracker (GitHub activity monitoring)
  - [ ] README updated with multi-source parser docs + cron setup (quickstart already exists)
  - [ ] Demo script: fake startup through full pipeline
- **Plans:** 0/0

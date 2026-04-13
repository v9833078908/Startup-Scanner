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

### Phase 2: Multi-Source + Delivery
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

### Phase 3: Research Quality + Architecture
- **Goal:** Real web search research (not LLM hallucination), clean architecture, incremental processing
- **Depends on:** Phase 1 (can run parallel with Phase 2)
- **Requirements:** R16-R17, R18-R19
- **Success Criteria:**
  - [ ] Merge invest_*/build_* into parameterized track modules (track_research.py, track_gate.py — pipeline_tracks config already controls tracks, but Python code still duplicated)
  - [ ] Verify web search quality across backends (DDG/Exa/Sonar via lib/web_search.py abstraction)
  - [ ] GitHub API enrichment (stars, forks, contributors, commit activity)
  - [ ] Incremental pipeline: process only new ideas since last run
  - [ ] Prompt versioning + cost tracking per run
  - [ ] Unit tests for routing/gating/scoring pure functions
  - [ ] core/ abstraction layer (idea_store, research_store, analysis_store)
- **Plans:** 0/0

### Phase 4: Production Polish
- **Goal:** Noise filtering, advanced features, documentation, demo readiness
- **Depends on:** Phase 2 + Phase 3
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

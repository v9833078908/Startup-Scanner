# Phase 2: Deep Research + Pipeline Quality Upgrade - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Source:** PRD Express Path (docs/Deep Analysis Upgrade Plan.md + Meeting 04.13.26)

<domain>
## Phase Boundary

This phase upgrades Stages 7.5, 8, and 9 of the pipeline. Stages 1-7 are NOT modified.

**Before:** Stage 7 (Build Gate) → Stage 8 (Deep Analysis on scarce data) → Stage 9 (Digest with "empty sounds")
**After:** Stage 7 (Build Gate) → Stage 7.5 [NEW] (Deep Research via Parallel AI) → Stage 8 (Kill signals + scoring on rich data + executive summary) → Stage 9 (Informative management digest)

Deliverable: full pipeline run producing a management-ready digest with executive summaries per startup.

</domain>

<decisions>
## Implementation Decisions

### Deep Research API
- Use Parallel AI Task API (https://api.parallel.ai/v1/tasks/runs) for autonomous deep research
- Processor tier: `base` ($0.005/run) or `core` ($0.025/run) — start with `core` for quality, downgrade if budget tight
- Auth: `PARALLEL_API_KEY` env var, header `x-api-key`
- Workflow: POST create task → poll GET result (timeout 600s default)
- Output schema: `type: "text"` for markdown research report with citations
- Budget constraint: ~$50/week for ~20 startups → ~$2.50/startup max

### Stage 7.5: Deep Research
- New file: `pipeline/deep_research.py`
- New file: `lib/parallel_client.py` — async wrapper for Parallel AI Task API
- New prompt: `prompts/deep_research_brief.md`
- Research scope per startup: бизнес-суть, TAM, конкуренты (глобальные + целевые рынки), traction/валидация, build assessment (техническая сложность, time to MVP, time to revenue, риски), рекомендация по географии
- Output: `2_research/{slug}/deep_research.md` — full research report (800-1500 words, Russian, tech terms in English)
- Only runs for startups that passed build gate (~11-20 from ~400)
- Idempotent: skip if deep_research.md already exists
- Concurrency: asyncio with semaphore (e.g., 3-5 concurrent)

### Stage 8: Deep Analysis Update
- Modify existing `pipeline/deep_analysis.py`
- Update prompt: `prompts/deep_analysis.md`
- NEW: Read `deep_research.md` as primary input (instead of scarce research notes)
- NEW: Kill signals checked BEFORE scoring — if any triggered → verdict PASS immediately:
  1. Рынок занят — сильный локальный игрок >30% доли на целевом рынке
  2. Высокий капитал на вход — значительные инвестиции для MVP (инфраструктура, лицензии, hardware)
  3. Далеко от компетенций i-Free — requires biotech, hardware, deep domain expertise
  4. >6 месяцев до первой выручки — от старта разработки до первых платящих клиентов
- NEW: Executive summary per startup (markdown block in analysis output):
  - Суть (2-3 предложения)
  - Рынок (TAM, рост, игроки)
  - Что строить (MVP scope, первые клиенты, канал продаж)
  - Целевой рынок (география + почему)
  - Time to market (до MVP / до первой выручки)
  - Ключевые риски (2-3)
  - Вердикт + одно предложение почему
- Scoring backend preserved (in md files), NOT shown in digest output
- Kill signal results stored in frontmatter: `killed: true/false`, `kill_reason: "..."`

### Stage 9: Digest Update
- Modify existing `pipeline/digest_generator.py`
- Update prompt: `prompts/digest.md`
- Executive summaries from Stage 8 go directly into digest (not re-synthesized)
- No numeric scoring in digest output
- PASS startups shown with kill-signal reason (transparency)
- WATCH/MONITOR: 2-3 informative sentences (not one-liners)
- Sections: Pipeline Summary, Ключевые находки, BUILD рекомендации, WATCH/MONITOR, PASS с kill-сигналами, Тренды недели

### Config Updates
- `config/scoring_weights.yaml`: build_mode criteria aligned with new weights table (same weights, same criteria)
- `config/triage.yaml`: no changes
- `.env`: add `PARALLEL_API_KEY` documentation

### Claude's Discretion
- Exact implementation of parallel_client.py (httpx async vs `parallel` Python SDK)
- Error handling strategy for Parallel AI API failures (retry logic, fallback)
- Exact semaphore count for concurrent deep research requests
- Whether to use `parallel` Python package or raw httpx calls
- Exact prompt wording (use the spec as basis, adjust for Parallel AI input format)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Upgrade Specification
- `docs/Deep Analysis Upgrade Plan.md` — Complete spec: problem statement, architecture, prompts, output formats, implementation plan

### Existing Pipeline Code (to be modified)
- `pipeline/deep_analysis.py` — Current Stage 8 implementation (analyze_one, run_deep_analysis)
- `pipeline/digest_generator.py` — Current Stage 9 implementation (LLM-based + template fallback)
- `pipeline/build_research.py` — Current Stage 5 (reference for research pattern)
- `run_pipeline.py` — Main orchestrator (needs Stage 7.5 wiring)

### Existing Prompts (to be modified)
- `prompts/deep_analysis.md` — Current analysis prompt (dual scoring)
- `prompts/digest.md` — Current digest prompt

### Infrastructure
- `lib/llm.py` — LLM client (call_llm, load_prompt) — reuse patterns
- `lib/web_search.py` — Web search abstraction (reference for Sonar integration pattern)
- `lib/utils.py` — Shared utilities (make_slug, load_idea)
- `config/scoring_weights.yaml` — Build/invest scoring weights

### Data Contracts
- `2_research/{slug}/` — Research output directory structure
- `3_analysis/{slug}_analysis.md` — Analysis output format with frontmatter

</canonical_refs>

<specifics>
## Specific Ideas

### Parallel AI Task API Integration
- Endpoint: POST https://api.parallel.ai/v1/tasks/runs
- Auth: x-api-key header
- Request: `{processor: "core", input: "research brief text", task_spec: {output_schema: {type: "text", description: "..."}}}`
- Result: GET https://api.parallel.ai/v1/tasks/runs/{run_id}/result (blocks until complete, timeout=600)
- Response includes `output.content` (research text) and `output.basis` (citations with url, title, excerpts, confidence)

### Research Brief Template (from spec)
The prompt should ask Parallel AI to research:
1. Суть бизнеса (механика, проблема, ICP, бизнес-модель)
2. Размер рынка (bottom-up TAM, динамика, драйверы)
3. Конкурентная среда (глобальные, целевые рынки — Россия/СНГ/MENA/SEA/LATAM)
4. Валидация и traction (выручка, пользователи, отзывы, инвесторы)
5. Оценка возможности build (техническая сложность, time to MVP, time to revenue, регуляторные барьеры, риски)
6. Рекомендация по географии (данные, не предустановка "СНГ")

</specifics>

<deferred>
## Deferred Ideas

- Few-shot examples for calibrating analysis (needs manual labeling from Дина + Илья)
- B2C segment support (Дина interested, do after build mode stabilizes)
- Multi-agent architecture / LangChain refactor (next major phase)
- A/B testing across multiple research APIs (start with Parallel AI, compare later)

</deferred>

---

*Phase: 02-deep-research-pipeline-quality-upgrade*
*Context gathered: 2026-04-13 via PRD Express Path*

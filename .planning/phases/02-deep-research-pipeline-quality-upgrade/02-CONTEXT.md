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
- **Canonical module name:** `pipeline/deep_research_v2.py` (NOT `deep_research.py` — legacy file with that name exists from Phase 01-04, kept for backward compat). The `_v2` suffix is the official permanent name for Phase 2; rename only happens during Phase 4 cleanup.
- New file: `lib/parallel_client.py` — async wrapper for Parallel AI Task API
- New prompt: `prompts/deep_research_brief.md`
- Research scope per startup: бизнес-суть, TAM, конкуренты (глобальные + целевые рынки), traction/валидация, build assessment (техническая сложность, time to MVP, time to revenue, риски), рекомендация по географии
- Output: `2_research/{slug}/deep_research.md` — full research report (800-1500 words, Russian, tech terms in English)
- Only runs for startups that passed build gate (~11-20 from ~400)
- Idempotent: skip if deep_research.md already exists
- Concurrency: asyncio with semaphore (e.g., 3-5 concurrent)
- **Accepted limitation:** Failed Parallel AI calls write a stub `(Deep research failed: ...)` to deep_research.md. Re-runs skip stubs (idempotency). To retry: manually delete the stub file before re-running. This is a known limitation accepted for Phase 2; auto-retry deferred to Phase 4.

### Verdict Taxonomy (CANONICAL — used in code, prompts, frontmatter, digest)
- `build_verdict` ∈ `{BUILD, PARTNER, MONITOR, SKIP}` — 4 values only, no PASS overload
- `killed: bool` + `kill_reason: str` — separate flags, NEVER folded into build_verdict
- A killed startup keeps its computed `build_verdict` (e.g. could be BUILD on numbers) but is filtered out of BUILD/PARTNER/MONITOR digest sections by `killed=True` check. Shown only in "PASS via kill signal" section.
- Digest verdict labels match exactly: `BUILD`, `PARTNER`, `MONITOR`, `SKIP`. WATCH never appears (it was an invest-track label removed in build-only architecture).

### Stage 8: Deep Analysis Update (BUILD-ONLY)
- Modify existing `pipeline/deep_analysis.py`
- Update prompt: `prompts/deep_analysis.md`
- NEW: Read `deep_research.md` as primary input (instead of scarce research notes)
- NEW: Kill signals checked BEFORE scoring — if any triggered, set `killed=True`, `kill_reason="..."` but STILL compute build_verdict (informational). The killed flag controls digest routing, not the verdict label. Four signals:
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

### Stage 9: Digest Update — DETERMINISTIC-FIRST
- Modify existing `pipeline/digest_generator.py`
- Update prompt: `prompts/digest.md` (now narrow scope — only Key Findings + Trends sections)
- **Deterministic sections (Python templates, no LLM):** Pipeline Summary, BUILD Recommendations (paste executive_summary byte-for-byte), MONITOR (paste executive_summary or 2-3 sentences from analysis), PASS via kill signals (table: name + kill_reason).
- **LLM sections (narrow scope only):** "Ключевые находки недели" (synthesis across all startups, 2-3 sentences) + "Тренды недели" (top categories + patterns). LLM never touches per-startup executive summaries.
- No numeric scoring anywhere in digest output
- Sections: Pipeline Summary → Ключевые находки → BUILD рекомендации → MONITOR → PASS via kill → Тренды недели
- Rationale: original LLM-first path violates the "executive summaries go directly, not re-synthesized" promise. Deterministic-first guarantees Stage 8 wording survives intact.

### Orchestrator: Honest Track Configuration
- run_pipeline.py MUST raise (or log error + force build-only) if `pipeline_tracks.invest: true` AND `pipeline_tracks.build` AND deep_analysis is run. Phase 2 deep_analysis.py is BUILD-ONLY by design — silently running it on invest-routed startups would produce build scoring on invest candidates. Honest failure is better than silent confusion.
- ROADMAP.md and README.md must explicitly state: "Invest deep analysis temporarily not supported in Phase 2 — will be re-added with separate prompt in future phase."

### Config Updates
- `config/scoring_weights.yaml`: build_mode criteria aligned with new weights table (same weights, same criteria); invest_mode preserved untouched for future
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

# Phase 08: Invest/Build Track Split — Context

**Gathered:** 2026-04-10
**Status:** Ready for planning
**Source:** User requirements from session discussion

<domain>
## Phase Boundary

Split the unified pipeline into two tracks after triage. Currently all 270+ startups go through the same research/gate/analysis pipeline regardless of whether they're interesting for invest or build. This wastes expensive LLM calls and produces irrelevant data (founder research for build-only candidates, CIS gap analysis for invest-only candidates).

Target architecture:
```
parse → prefilter → triage ─┬─ route="invest" → invest research → invest gate → heavy analysis
                             ├─ route="build"  → build research  → build gate  → build analysis
                             ├─ route="both"   → both tracks
                             └─ route="skip"   → archive
```

</domain>

<decisions>
## Implementation Decisions

### Triage Prompt — Add Build Signals
The triage prompt currently only asks invest questions (has_product_evidence, has_founder_signal). Must add three build-specific signals that CAN be evaluated on thin data:

1. **replicability** ("easy" / "medium" / "hard" / "impossible") — Can a small team build this in 2-3 months? "AI-powered satellite imagery analysis" = impossible. "Notion template marketplace" = easy. LLM can judge from one-line description.

2. **cis_gap_likelihood** (bool) — Is this product US/EU-focused with no obvious CIS analogue? Rough heuristic acceptable at triage stage.

3. **stack_fit** (bool) — Does it match iFree competencies (AI, fintech, gamedev, devtools, infra, automation)?

### Triage Output Structure
```yaml
# Common fields
category: "AI code review"
one_liner: "..."
barriers: [...]

# Invest-track signals
has_product_evidence: false
has_founder_signal: false
invest_priority: "low" | "medium" | "high"

# Build-track signals
replicability: "easy" | "medium" | "hard" | "impossible"
stack_fit: true | false
build_candidate: true | false

# Routing
route: "invest" | "build" | "both" | "skip"
```

### Route Field — Key Decision
`route` determines which pipeline track(s) the startup enters:
- **invest**: invest_priority high/medium AND NOT build_candidate → invest research only
- **build**: build_candidate AND invest_priority low → build research only  
- **both**: invest_priority high/medium AND build_candidate → both tracks
- **skip**: invest_priority low AND NOT build_candidate → skip research

### Build Candidate — Tighter Definition
Current build_candidate is too loose (78% pass — any is_tech + software + sector_match). New definition should require: is_tech + software/service + sector_match + replicability in (easy, medium) + stack_fit. This should reduce pass rate from 78% to ~20-30%.

### Dual Research Prompts
- **Invest research prompt**: Search for "{name}" founders, team, traction, revenue, customers
- **Build research prompt**: Search for "{category}" in Russia/CIS, check GitHub for OSS alternatives, estimate cost-to-build, identify competitors in CIS market

### Dual Research Gates
- **Invest gate**: Has enough team/traction/competitive data for invest scoring? (2/3 evidence fields)
- **Build gate**: Is there a real CIS gap? Is it replicable? Is there an OSS base to build on?

### Exa Search Integration
Replace LLM-synthesized research with real web search via Exa API. Exa key in .env as EXA_API_KEY. Use exa-py SDK. Different search queries per track.

### Pipeline Architecture
run_pipeline.py must fork after triage based on route field. Invest and build tracks can run in parallel (different startups, different research dirs).

</decisions>

<canonical_refs>
## Canonical References

### Pipeline Code
- `pipeline/triage.py` — Current triage implementation (to be modified)
- `pipeline/deep_research.py` — Current unified research (to be split)
- `pipeline/research_gate.py` — Current unified gate (to be split)
- `run_pipeline.py` — Pipeline orchestrator (to be updated)
- `prompts/triage.md` — Current triage prompt (to be extended)
- `prompts/research_gate.md` — Current gate prompt (to be split)

### Config
- `config/triage.yaml` — Triage thresholds and gate config
- `SCHEMA.md` — File contracts
- `THESIS.md` — Investment thesis and build patterns

</canonical_refs>

<specifics>
## Specific Ideas

- Exa API for web search (exa-py SDK, OpenAI-compatible-ish)
- Build research should search: "{category} Россия" OR "{category} CIS" OR "{category} аналог"
- Invest research should search: "{name} founders" OR "{name} funding" OR "{name} traction"
- Research results saved as separate files: invest_research.md / build_research.md in 2_research/{slug}/
- Gate results in gate_invest.md / gate_build.md

</specifics>

<deferred>
## Deferred Ideas

- Perplexity as alternative to Exa (evaluate after seeing Exa quality)
- GitHub API integration for OSS metrics (separate phase)
- LinkedIn scraping for founder data (legal concerns, separate phase)

</deferred>

---

*Phase: 01-mvp-dealpad-pipeline-end-to-end (plans 08-10)*
*Context gathered: 2026-04-10 via user session discussion*

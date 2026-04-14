"""Stage 9 — Digest Generator (DETERMINISTIC-FIRST).

Architecture
------------
Per 02-CONTEXT.md "Stage 9: Digest Update — DETERMINISTIC-FIRST":

- Hand-built sections (Python templates, NO LLM):
  * Pipeline Summary
  * BUILD рекомендации (executive_summary pasted BYTE-FOR-BYTE)
  * MONITOR (executive_summary pasted BYTE-FOR-BYTE)
  * PASS via kill signals (table with kill_reason)

- LLM-narrow sections (synthesis only):
  * Ключевые находки недели (2-3 sentences synthesized across all startups)
  * Тренды недели (top categories + patterns)

The LLM NEVER sees per-startup executive_summaries — they are composed by Python
directly. This guarantees Stage 8 wording survives intact into the digest and
avoids the paraphrase/compress failure mode of LLM-first digest generation.

No numeric scoring appears anywhere in the rendered digest (scores live in
3_analysis/ files for audit trail only).

Verdict taxonomy (from Plan 02-02): build_verdict ∈ {BUILD, PARTNER, MONITOR, SKIP}.
Killed startups keep their computed verdict and are filtered via the `killed` flag,
not relabelled.

Backward compat: legacy analysis files from pre-Plan-02 runs may still carry
invest_total/invest_verdict frontmatter. collect_analyses uses post.get() with
defaults — never raises KeyError on missing invest fields.
"""

import asyncio
import datetime
import json
import logging
import os
import time
from collections import Counter
from pathlib import Path

import frontmatter

from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, make_slug

log = logging.getLogger("pipeline.digest")

IDEAS_DIR = Path("1_ideas")
ANALYSIS_DIR = Path("3_analysis")
ARCHIVE_DIR = Path("_archive")
DIGESTS_DIR = Path("digests")
RESEARCH_DIR = Path("2_research")


# ---------------------------------------------------------------------------
# Stats collection
# ---------------------------------------------------------------------------

def collect_pipeline_stats() -> dict:
    """Count items at each pipeline stage.

    Updates in Plan 02-03:
    - `researched` counter now checks for web_research.md OR build_research.md
      OR deep_research.md (was legacy-only, which made the digest show 0 after
      Phase 2 reshuffling).
    - `deep_researched` new counter — Stage 7.5 visibility.
    - `killed` new counter — PASS via kill signal section needs this.
    """
    total = len(list(IDEAS_DIR.glob("*.md")))
    archived = len(list(ARCHIVE_DIR.glob("*.md"))) if ARCHIVE_DIR.exists() else 0

    triaged = 0
    priority_dist = {"high": 0, "medium": 0, "low": 0}
    build_candidates = 0
    research_candidates = 0
    route_dist = {"invest": 0, "build": 0, "both": 0, "skip": 0}

    for idea_file in IDEAS_DIR.glob("*.md"):
        try:
            post = load_idea(idea_file)
            if "invest_priority" in post.metadata:
                triaged += 1
                priority = post.get("invest_priority", "low")
                priority_dist[priority] = priority_dist.get(priority, 0) + 1
                if post.get("build_candidate"):
                    build_candidates += 1
                if priority in ("high", "medium") or post.get("build_candidate"):
                    research_candidates += 1
            route = post.get("route")
            if route in route_dist:
                route_dist[route] += 1
        except Exception:
            continue

    # Researched: any of the known research artifact files
    researched = len([
        d for d in RESEARCH_DIR.iterdir()
        if d.is_dir() and any(
            (d / f).exists()
            for f in ("web_research.md", "build_research.md", "deep_research.md")
        )
    ]) if RESEARCH_DIR.exists() else 0

    # Deep researched: Stage 7.5 output specifically
    deep_researched = len([
        d for d in RESEARCH_DIR.iterdir()
        if d.is_dir() and (d / "deep_research.md").exists()
    ]) if RESEARCH_DIR.exists() else 0

    analyzed = (
        len(list(ANALYSIS_DIR.glob("*_analysis.md")))
        if ANALYSIS_DIR.exists() else 0
    )

    killed_count = 0
    if ANALYSIS_DIR.exists():
        for f in ANALYSIS_DIR.glob("*_analysis.md"):
            try:
                if frontmatter.load(str(f)).get("killed", False):
                    killed_count += 1
            except Exception:
                continue

    return {
        "total": total,
        "archived": archived,
        "triaged": triaged,
        "priority_distribution": priority_dist,
        "route_distribution": route_dist,
        "build_candidates": build_candidates,
        "research_candidates": research_candidates,
        "researched": researched,
        "deep_researched": deep_researched,
        "analyzed": analyzed,
        "killed": killed_count,
    }


# ---------------------------------------------------------------------------
# Analysis collection
# ---------------------------------------------------------------------------

def collect_analyses() -> list[dict]:
    """Read all analysis files; return list sorted by build_total desc.

    Post-Plan-02 fields (required by the deterministic digest):
      killed, kill_reason, executive_summary, recommended_market, time_to_mvp,
      time_to_revenue.

    Backward compat: old analysis files may still carry invest_total/invest_verdict.
    We use post.get() with defaults so a missing invest field does NOT raise.
    """
    analyses = []

    # slug -> idea lookup (category/round/one_liner fallbacks)
    idea_map = {}
    for idea_file in IDEAS_DIR.glob("*.md"):
        try:
            idea = load_idea(idea_file)
            idea_slug = make_slug(idea.get("name", ""))
            idea_map[idea_slug] = idea
        except Exception:
            continue

    for analysis_file in ANALYSIS_DIR.glob("*_analysis.md"):
        try:
            post = frontmatter.load(str(analysis_file))
            slug = analysis_file.stem.replace("_analysis", "")

            # Enrich from idea file (category/round/one_liner not stored in analysis)
            idea = idea_map.get(slug)
            category = post.get("category", "Unknown")
            round_raw = post.get("round_raw", "Unknown")
            one_liner = ""
            if idea:
                if category == "Unknown":
                    category = idea.get("category", "Unknown")
                if round_raw == "Unknown":
                    round_raw = idea.get("round_raw", "Unknown")
                one_liner = idea.get("one_liner", "")

            analyses.append(
                {
                    "slug": slug,
                    "name": post.get("name", slug),
                    "url": post.get("url", ""),
                    # Build-only (Plan 02-02)
                    "build_total": post.get("build_total", 0),
                    "build_verdict": post.get("build_verdict", "SKIP"),
                    "killed": bool(post.get("killed", False)),
                    "kill_reason": post.get("kill_reason", "") or "",
                    "executive_summary": post.get("executive_summary", "") or "",
                    "recommended_market": post.get("recommended_market", "") or "",
                    "time_to_mvp": post.get("time_to_mvp", "") or "",
                    "time_to_revenue": post.get("time_to_revenue", "") or "",
                    # Legacy invest fields — keep for backward compat, NOT rendered
                    "invest_total": post.get("invest_total", None),
                    "invest_verdict": post.get("invest_verdict", None),
                    # Enrichment
                    "category": category,
                    "round_raw": round_raw,
                    "one_liner": one_liner,
                    "content": post.content,
                }
            )
        except Exception as exc:
            log.warning("failed to load analysis %s: %s", analysis_file.name, exc)
            continue

    # Sort by build_total desc (build-first pipeline)
    analyses.sort(key=lambda x: x["build_total"], reverse=True)
    return analyses


# ---------------------------------------------------------------------------
# LLM synthesis (narrow scope — only key_findings + trends)
# ---------------------------------------------------------------------------

def _build_summary_payload(stats: dict, analyses: list[dict]) -> dict:
    """Aggregated payload for the narrow LLM synthesis call.

    Deliberately excludes executive_summary — Python handles per-startup blocks.
    The LLM only sees counts + minimal per-startup metadata to spot patterns.
    """
    slim = [
        {
            "name": a["name"],
            "category": a["category"],
            "build_verdict": a["build_verdict"],
            "killed": a["killed"],
            "kill_reason": a["kill_reason"] if a["killed"] else "",
            "recommended_market": a["recommended_market"],
        }
        for a in analyses
    ]

    return {
        "date": datetime.date.today().isoformat(),
        "counts": {
            "total": stats.get("total", 0),
            "archived": stats.get("archived", 0),
            "triaged": stats.get("triaged", 0),
            "research_candidates": stats.get("research_candidates", 0),
            "researched": stats.get("researched", 0),
            "deep_researched": stats.get("deep_researched", 0),
            "analyzed": stats.get("analyzed", 0),
            "killed": stats.get("killed", 0),
        },
        "route_distribution": stats.get("route_distribution", {}),
        "analyses": slim,
    }


async def generate_synthesis_with_llm(
    stats: dict, analyses: list[dict]
) -> dict:
    """Narrow LLM call — returns only {key_findings, trends}.

    Never raises. On failure, returns sentinel strings so the deterministic
    digest can still render the other 4 sections without interruption.
    """
    fallback = {
        "key_findings": "_(LLM synthesis unavailable — см. 3_analysis/ per-startup details)_",
        "trends": "_(LLM synthesis unavailable — см. 3_analysis/ per-startup details)_",
    }

    if not analyses:
        return {
            "key_findings": "На этой неделе нет проанализированных стартапов.",
            "trends": "Недостаточно данных для выводов.",
        }

    try:
        payload = _build_summary_payload(stats, analyses)
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
        prompt = load_prompt("digest").replace("{summary_data}", payload_json)

        result = await call_llm(
            prompt,
            model=os.getenv("OPENROUTER_MODEL_LIGHT"),
            json_mode=True,
            temperature=0.2,
        )

        if isinstance(result, Exception) or result is None:
            log.warning("LLM synthesis failed — using fallback")
            return fallback

        if isinstance(result, dict):
            return {
                "key_findings": str(
                    result.get("key_findings")
                    or fallback["key_findings"]
                ),
                "trends": str(result.get("trends") or fallback["trends"]),
            }

        # Unexpected shape (e.g. string back from json_mode failure path)
        log.warning("LLM synthesis returned unexpected shape: %r", type(result))
        return fallback
    except Exception as exc:
        log.warning("generate_synthesis_with_llm failed: %s", exc)
        return fallback


# ---------------------------------------------------------------------------
# Deterministic digest builder
# ---------------------------------------------------------------------------

def _render_startup_block(a: dict) -> str:
    """Render one BUILD/MONITOR startup block.

    executive_summary goes byte-for-byte (no LLM rewriting). Metadata line
    (round/category/URL) is appended afterwards.
    """
    exec_sum = (a.get("executive_summary") or "").strip() or "_(executive_summary отсутствует)_"
    round_raw = a.get("round_raw") or "Unknown"
    category = a.get("category") or "Unknown"
    url = a.get("url") or ""
    return (
        f"### {a['name']} — {a['build_verdict']}\n"
        f"\n"
        f"{exec_sum}\n"
        f"\n"
        f"**Round:** {round_raw} | **Category:** {category} | **URL:** {url}\n"
    )


def build_digest_deterministic(
    stats: dict, analyses: list[dict], llm_synthesis: dict
) -> str:
    """Primary digest builder — 6 sections, Python templates with narrow LLM inserts.

    Section layout (per 02-CONTEXT.md decisions):
      1. Pipeline Summary — from `stats`
      2. Ключевые находки недели — insert `llm_synthesis["key_findings"]`
      3. BUILD рекомендации — each a where build_verdict ∈ {BUILD, PARTNER} AND not killed
      4. MONITOR — each a where build_verdict == MONITOR AND not killed
      5. PASS via kill signals — table rows for killed==True
      6. Тренды недели — insert `llm_synthesis["trends"]`
    """
    today = datetime.date.today().isoformat()

    pd_dist = stats.get("priority_distribution", {})
    rd_dist = stats.get("route_distribution", {})

    parts: list[str] = []

    parts.append(f"# Startup Scouting Digest — неделя {today}")
    parts.append("")

    # 1 — Pipeline Summary (deterministic)
    parts.append("## Pipeline Summary")
    parts.append("")
    parts.append(f"- **Parsed:** {stats.get('total', 0)} startups (archived: {stats.get('archived', 0)})")
    parts.append(
        f"- **Triaged:** {stats.get('triaged', 0)} "
        f"(high={pd_dist.get('high', 0)}, "
        f"medium={pd_dist.get('medium', 0)}, "
        f"low={pd_dist.get('low', 0)})"
    )
    parts.append(
        f"- **Route distribution:** invest={rd_dist.get('invest', 0)}, "
        f"build={rd_dist.get('build', 0)}, "
        f"both={rd_dist.get('both', 0)}, "
        f"skip={rd_dist.get('skip', 0)}"
    )
    parts.append(f"- **Research candidates:** {stats.get('research_candidates', 0)}")
    parts.append(f"- **Researched:** {stats.get('researched', 0)}")
    parts.append(f"- **Deep researched (Stage 7.5):** {stats.get('deep_researched', 0)}")
    parts.append(f"- **Analyzed:** {stats.get('analyzed', 0)}")
    parts.append(f"- **Killed (kill signals):** {stats.get('killed', 0)}")
    parts.append("")

    # 2 — Ключевые находки (LLM synthesis insert)
    parts.append("## Ключевые находки недели")
    parts.append("")
    parts.append(llm_synthesis.get("key_findings", "").strip() or "_(нет данных)_")
    parts.append("")

    # 3 — BUILD рекомендации (deterministic, byte-for-byte exec summary)
    build_recs = [
        a for a in analyses
        if a.get("build_verdict") in ("BUILD", "PARTNER") and not a.get("killed")
    ]
    parts.append("## BUILD рекомендации")
    parts.append("")
    if build_recs:
        for a in build_recs:
            parts.append(_render_startup_block(a))
            parts.append("")
    else:
        parts.append("_На этой неделе нет BUILD/PARTNER рекомендаций._")
        parts.append("")

    # 4 — MONITOR (deterministic, byte-for-byte exec summary)
    monitors = [
        a for a in analyses
        if a.get("build_verdict") == "MONITOR" and not a.get("killed")
    ]
    parts.append("## MONITOR")
    parts.append("")
    if monitors:
        for a in monitors:
            parts.append(_render_startup_block(a))
            parts.append("")
    else:
        parts.append("_Нет стартапов в статусе MONITOR._")
        parts.append("")

    # 5 — PASS via kill signals (deterministic table)
    killed = [a for a in analyses if a.get("killed")]
    parts.append("## PASS via kill signals")
    parts.append("")
    if killed:
        parts.append("| Name | Category | Kill reason |")
        parts.append("|------|----------|-------------|")
        for a in killed:
            name = str(a["name"]).replace("|", "/")
            cat = str(a.get("category", "")).replace("|", "/")
            reason = str(a.get("kill_reason", "")).replace("|", "/").replace("\n", " ")
            if not reason:
                reason = "(нет описания)"
            parts.append(f"| {name} | {cat} | {reason} |")
    else:
        parts.append("_На этой неделе нет стартапов, отсечённых kill-сигналами._")
    parts.append("")

    # 6 — Тренды недели (LLM synthesis insert)
    parts.append("## Тренды недели")
    parts.append("")
    parts.append(llm_synthesis.get("trends", "").strip() or "_(нет данных)_")
    parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def run_digest() -> dict:
    """Stage 9 entry point.

    Flow: collect_analyses → collect_pipeline_stats → generate_synthesis_with_llm
    → build_digest_deterministic → write file. No LLM-vs-template branching —
    the LLM is only ever used for the two narrow synthesis sections.
    """
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)

    stats = collect_pipeline_stats()
    analyses = collect_analyses()

    if not analyses:
        log.warning("no analysis files found in 3_analysis/ — generating minimal digest")

    t0 = time.monotonic()
    llm_synthesis = await generate_synthesis_with_llm(stats, analyses)
    synth_elapsed = time.monotonic() - t0
    log.info("Digest synthesis done in %.1fs", synth_elapsed)

    digest_md = build_digest_deterministic(stats, analyses, llm_synthesis)

    # Filename: {YYYY}-W{WW}_weekly.md. Never overwrite — append _run2, _run3, …
    today = datetime.date.today()
    week_num = today.isocalendar()[1]
    base_name = f"{today.year}-W{week_num:02d}_weekly"
    output_path = DIGESTS_DIR / f"{base_name}.md"

    if output_path.exists():
        run = 2
        while (DIGESTS_DIR / f"{base_name}_run{run}.md").exists():
            run += 1
        output_path = DIGESTS_DIR / f"{base_name}_run{run}.md"

    output_path.write_text(digest_md, encoding="utf-8")
    log.info("Digest saved to %s", output_path)

    return {
        "digest_path": str(output_path),
        "stats": stats,
        "analysis_count": len(analyses),
    }


if __name__ == "__main__":
    asyncio.run(run_digest())

"""Stage 8 — Deep Analysis (BUILD-ONLY).

Reads the rich `deep_research.md` produced by Stage 7.5 (pipeline/deep_research_v2.py),
applies 4 kill signals as a hard pre-scoring filter, then computes BUILD-mode
scoring and an executive summary for the digest.

Architecture notes
------------------
BUILD-ONLY: invest-mode scoring has been removed from this stage (prompt, code,
frontmatter, body). Rationale:
  - Anchoring bias when both scorings live in the same LLM context window.
  - Invest-mode is disabled by default in config/triage.yaml
    (pipeline_tracks.invest: false).
  - When invest-mode is re-introduced it will be a separate prompt + LLM call
    (tracked in ROADMAP.md).

The invest_mode section in config/scoring_weights.yaml is intentionally
preserved untouched for that future re-introduction.

Verdict taxonomy (canonical)
----------------------------
`build_verdict` ∈ {BUILD, PARTNER, MONITOR, SKIP} — 4 values only. Never PASS,
never WATCH. Killed startups keep their computed verdict; the `killed` flag
controls digest routing (digest filters by killed=True, not by verdict label).
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import frontmatter
import yaml

from lib.llm import call_llm, load_prompt
from lib.utils import make_slug, load_idea

log = logging.getLogger("pipeline.deep_analysis")

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")
ANALYSIS_DIR = Path("3_analysis")
WEIGHTS_PATH = Path("config/scoring_weights.yaml")

VALID_BUILD_VERDICTS = {"BUILD", "PARTNER", "MONITOR", "SKIP"}


def load_weights() -> dict:
    return yaml.safe_load(WEIGHTS_PATH.read_text(encoding="utf-8"))


def compute_weighted_score(scores: dict, weights: dict) -> float:
    total = 0.0
    for criterion, weight in weights.items():
        raw = scores.get(criterion, 0)
        # Each criterion value may be a dict {score: N, rationale: "..."} or a plain number
        if isinstance(raw, dict):
            score = float(raw.get("score", 0))
        else:
            score = float(raw)
        total += score * weight
    return round(total, 1)


def determine_verdict(score: float, thresholds: dict) -> str:
    # Sort thresholds descending by value; return first label where score >= threshold
    sorted_thresholds = sorted(thresholds.items(), key=lambda x: x[1], reverse=True)
    for label, threshold in sorted_thresholds:
        if score >= threshold:
            return label.upper()
    # Fallback to the lowest threshold label
    return sorted_thresholds[-1][0].upper()


async def analyze_one(
    post: frontmatter.Post,
    slug: str,
    research_dir: Path,
    prompt_template: str,
    weights: dict,
) -> dict:
    """Analyze a single startup — BUILD-ONLY.

    Reads deep_research.md (primary data source) and legacy research files
    (fallback context only). Applies kill signals, computes build scoring,
    writes analysis file with executive_summary in frontmatter.
    """
    # Primary input: deep_research.md from Stage 7.5 (rich 800-1500 word report)
    deep_research_path = research_dir / "deep_research.md"
    deep_research_content = (
        deep_research_path.read_text(encoding="utf-8")
        if deep_research_path.exists()
        else ""
    )

    # Legacy research notes — kept as fallback context, not primary input
    website_path = research_dir / "website.md"
    website_content = (
        website_path.read_text(encoding="utf-8") if website_path.exists() else ""
    )

    research_notes = ""
    for research_file in ("invest_research.md", "build_research.md", "web_research.md"):
        rp = research_dir / research_file
        if rp.exists():
            research_notes += rp.read_text(encoding="utf-8") + "\n\n"
    research_notes = research_notes.strip()

    name = post.get("name", slug) or slug
    url = post.get("url", "") or ""
    round_raw = post.get("round_raw", "Unknown") or "Unknown"
    description = post.content or ""
    # build_thesis: triage-LLM hypothesis (added 2026-04-14 after triage refactor).
    # Missing/empty → "(none)" so prompt still reads well.
    build_thesis = post.get("build_thesis") or "(none)"

    # Build prompt via .replace() chain — required because the prompt contains
    # literal JSON braces that would break str.format (see Phase 01 decisions).
    prompt = (
        prompt_template
        .replace("{name}", str(name))
        .replace("{url}", str(url))
        .replace("{round_raw}", str(round_raw))
        .replace("{description}", str(description))
        .replace("{build_thesis}", str(build_thesis))
        # Deep research is the primary source — generous 8000 char budget.
        .replace("{deep_research_content}", deep_research_content[:8000])
        .replace("{website_content}", website_content[:3000])
        .replace("{research_notes}", research_notes[:3000])
    )

    result = await call_llm(
        prompt,
        model=os.getenv("OPENROUTER_MODEL_HEAVY"),
        json_mode=True,
        temperature=0.2,
    )

    if isinstance(result, Exception):
        raise result
    if result is None:
        # call_llm returns None after 3 JSON-parse failures — surface as an exception
        # so run_deep_analysis counts it as failed rather than writing a broken file.
        raise RuntimeError(f"LLM returned no parseable JSON for {slug}")

    # --- Kill signals ---
    kill_signals = result.get("kill_signals", {}) or {}
    killed = bool(result.get("killed", False))
    kill_reason = result.get("kill_reason", "") or ""
    if killed and not kill_reason:
        # Derive kill_reason from first triggered signal if LLM left it empty.
        for sig_name, sig_data in kill_signals.items():
            if isinstance(sig_data, dict) and sig_data.get("triggered"):
                kill_reason = sig_data.get("reason") or sig_name
                break

    # --- Build scoring (BUILD-ONLY) ---
    # Killed startups keep their computed build_verdict — the killed flag controls
    # digest routing, NOT the verdict label. Verdict is never relabelled to any
    # invest-mode term; taxonomy is {BUILD, PARTNER, MONITOR, SKIP} only.
    build_scoring = result.get("build_scoring", {}) or {}
    build_total = compute_weighted_score(
        build_scoring, weights["build_mode"]["criteria"]
    )
    build_verdict = determine_verdict(build_total, weights["build_mode"]["thresholds"])
    # Sanity check — taxonomy per 02-CONTEXT.md
    assert build_verdict in VALID_BUILD_VERDICTS, (
        f"Invalid build_verdict={build_verdict!r} for {slug} — "
        "taxonomy must be {BUILD, PARTNER, MONITOR, SKIP}"
    )

    # --- Executive summary + auxiliary fields ---
    executive_summary = result.get("executive_summary", "") or ""
    recommended_market = result.get("recommended_market", "") or ""
    time_to_mvp = result.get("time_to_mvp", "") or ""
    time_to_revenue = result.get("time_to_revenue", "") or ""

    analyzed_at = datetime.utcnow().isoformat()

    # --- Body markdown assembly ---
    def _criterion_lines(scoring: dict, criteria_weights: dict) -> str:
        lines = []
        for criterion in criteria_weights:
            raw = scoring.get(criterion, {})
            if isinstance(raw, dict):
                score = raw.get("score", "?")
                rationale = raw.get("rationale", "")
            else:
                score = raw
                rationale = ""
            lines.append(f"- **{criterion}**: {score}/10 — {rationale}")
        return "\n".join(lines)

    def _bullet_list(items) -> str:
        if not items:
            return "- N/A"
        if isinstance(items, list):
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    build_lines = _criterion_lines(build_scoring, weights["build_mode"]["criteria"])

    parts = [f"# Analysis: {name}\n"]

    if killed:
        # Killed notice — informational. Computed build_verdict kept for traceability,
        # never relabelled (taxonomy is {BUILD, PARTNER, MONITOR, SKIP} only).
        parts.append(
            f"## Killed: {kill_reason}\n\n"
            f"_Computed verdict was **{build_verdict}** but this startup is flagged out "
            f"via kill signal. The digest routes killed startups into a dedicated "
            f"filtered-out section._\n"
        )

    # Executive summary always present (even if killed)
    parts.append(f"## Executive Summary\n\n{executive_summary or 'N/A'}\n")

    # Scoring detail — skip when killed (numbers are noise once kill flag is set)
    if not killed:
        parts.append(
            f"## Build Score: {build_total}/10 — {build_verdict}\n\n{build_lines}\n"
        )

    parts.append(f"## Recommended Market\n\n{recommended_market or 'N/A'}\n")
    parts.append(
        "## Time to Market\n\n"
        f"- MVP: {time_to_mvp or 'N/A'}\n"
        f"- First Revenue: {time_to_revenue or 'N/A'}\n"
    )
    parts.append(
        f"## Red Flags\n\n{_bullet_list(result.get('red_flags', []))}\n"
    )
    parts.append(
        f"## Green Flags\n\n{_bullet_list(result.get('green_flags', []))}\n"
    )
    parts.append(f"## Risks\n\n{_bullet_list(result.get('risks', []))}\n")
    parts.append(f"## Next Steps\n\n{_bullet_list(result.get('next_steps', []))}\n")

    body = "\n".join(parts)

    # --- Frontmatter write (BUILD-ONLY architecture) ---
    analysis_post = frontmatter.Post(
        body,
        name=name,
        url=url,
        build_total=build_total,
        build_verdict=build_verdict,
        analyzed_at=analyzed_at,
        killed=killed,
        kill_reason=kill_reason,
        executive_summary=executive_summary,
        recommended_market=recommended_market,
        time_to_mvp=time_to_mvp,
        time_to_revenue=time_to_revenue,
    )

    analysis_path = ANALYSIS_DIR / f"{slug}_analysis.md"
    analysis_path.write_text(frontmatter.dumps(analysis_post), encoding="utf-8")

    return {
        "slug": slug,
        "build_total": build_total,
        "build_verdict": build_verdict,
        "killed": killed,
        "kill_reason": kill_reason,
    }


async def run_deep_analysis(slugs: list[str] | None = None) -> dict:
    """Stage 8 entry point — run BUILD-ONLY deep analysis on a list of slugs.

    If `slugs` is None, auto-discover research dirs containing deep_research.md
    (preferred) or any legacy research file (fallback).
    """
    prompt_template = load_prompt("deep_analysis")
    weights = load_weights()
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    if slugs is None:
        # Prefer deep_research.md; fall back to legacy research files so this
        # still works for slugs that pre-date Stage 7.5.
        slugs = [
            d.name
            for d in sorted(RESEARCH_DIR.iterdir())
            if d.is_dir()
            and any(
                (d / f).exists()
                for f in (
                    "deep_research.md",
                    "web_research.md",
                    "build_research.md",
                    "invest_research.md",
                )
            )
        ]

    analysis_tasks = []
    skipped = 0

    for slug in slugs:
        # Idempotency: skip if already analyzed
        if (ANALYSIS_DIR / f"{slug}_analysis.md").exists():
            skipped += 1
            continue

        # Find matching idea file in IDEAS_DIR
        post = None
        for idea_file in sorted(IDEAS_DIR.glob("*.md")):
            try:
                candidate = load_idea(idea_file)
                if make_slug(candidate.get("name", "")) == slug:
                    post = candidate
                    break
            except Exception:
                continue

        if post is None:
            # Create minimal stub post so analysis can still proceed
            post = frontmatter.Post("", name=slug, url="")

        research_dir = RESEARCH_DIR / slug
        analysis_tasks.append(
            analyze_one(post, slug, research_dir, prompt_template, weights)
        )

    log.info(
        "Analyzing %d startups (skipping %d already analyzed)",
        len(analysis_tasks), skipped,
    )

    t0 = time.monotonic()
    results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

    success_count = sum(1 for r in results if not isinstance(r, Exception))
    fail_count = sum(1 for r in results if isinstance(r, Exception))

    for r in results:
        if isinstance(r, Exception):
            log.error("analysis failed: %s", r)

    elapsed = time.monotonic() - t0
    log.info(
        "=== deep_analysis done in %.1fs — analyzed=%d failed=%d ===",
        elapsed, success_count, fail_count,
    )

    return {"analyzed": success_count, "failed": fail_count}


if __name__ == "__main__":
    asyncio.run(run_deep_analysis())

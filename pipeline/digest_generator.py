import asyncio
import datetime
import json
import logging
import os
import time
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


def collect_pipeline_stats() -> dict:
    """Count items at each pipeline stage using triage fields."""
    total = len(list(IDEAS_DIR.glob("*.md")))
    archived = len(list(ARCHIVE_DIR.glob("*.md"))) if ARCHIVE_DIR.exists() else 0

    triaged = 0
    priority_dist = {"high": 0, "medium": 0, "low": 0}
    build_candidates = 0
    research_candidates = 0

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
        except Exception:
            continue

    researched = len([
        d for d in RESEARCH_DIR.iterdir()
        if d.is_dir() and (d / "web_research.md").exists()
    ]) if RESEARCH_DIR.exists() else 0

    analyzed = len(list(ANALYSIS_DIR.glob("*_analysis.md"))) if ANALYSIS_DIR.exists() else 0

    return {
        "total": total,
        "archived": archived,
        "triaged": triaged,
        "priority_distribution": priority_dist,
        "build_candidates": build_candidates,
        "research_candidates": research_candidates,
        "researched": researched,
        "analyzed": analyzed,
    }


def collect_analyses() -> list[dict]:
    """Read all analysis files and return sorted list of analysis dicts."""
    analyses = []

    for analysis_file in ANALYSIS_DIR.glob("*_analysis.md"):
        try:
            post = frontmatter.load(str(analysis_file))
            slug = analysis_file.stem.replace("_analysis", "")

            # Try to find matching idea file for category
            category = post.get("category", "Unknown")
            if category == "Unknown":
                for idea_file in IDEAS_DIR.glob("*.md"):
                    try:
                        idea = load_idea(idea_file)
                        if make_slug(idea.get("name", "")) == slug:
                            category = idea.get("category", "Unknown")
                            break
                    except Exception:
                        continue

            analyses.append(
                {
                    "name": post.get("name", slug),
                    "url": post.get("url", ""),
                    "invest_total": post.get("invest_total", 0),
                    "build_total": post.get("build_total", 0),
                    "invest_verdict": post.get("invest_verdict", "PASS"),
                    "build_verdict": post.get("build_verdict", "SKIP"),
                    "category": category,
                    "round_raw": post.get("round_raw", "Unknown"),
                    "content": post.content,
                }
            )
        except Exception:
            continue

    # Sort by invest_total descending
    analyses.sort(key=lambda x: x["invest_total"], reverse=True)
    return analyses


def build_digest_data(stats: dict, analyses: list[dict]) -> str:
    """Build JSON string of all data to pass to the LLM digest prompt."""
    data = {
        "stats": stats,
        "analyses": analyses,
        "date": datetime.date.today().isoformat(),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _extract_section(content: str, header: str) -> str:
    """Extract text from a markdown section by header name."""
    lines = content.split("\n")
    in_section = False
    section_lines = []
    for line in lines:
        if line.startswith("##") and header.lower() in line.lower():
            in_section = True
            continue
        if in_section:
            if line.startswith("##"):
                break
            section_lines.append(line)
    return "\n".join(section_lines).strip()


def build_digest_manually(stats: dict, analyses: list[dict]) -> str:
    """FALLBACK: Build digest without LLM using string formatting."""
    today = datetime.date.today().isoformat()

    invest_candidates = [a for a in analyses if a["invest_verdict"] == "INVEST"]
    watch_list = [a for a in analyses if a["invest_verdict"] == "WATCH"]
    build_opps = [
        a for a in analyses if a["build_verdict"] in ("BUILD", "PARTNER")
    ]

    priority_dist = stats.get("priority_distribution", {})

    # Pipeline Summary section
    lines = [
        f"# Startup Scouting Digest -- Week of {today}",
        "",
        "## Pipeline Summary",
        "",
        f"- **Parsed:** {stats['total']} startups from DealPad",
        f"- **After pre-filter:** {stats['total'] - stats['archived']} relevant"
        f" ({stats['archived']} archived)",
        f"- **Triaged:** {stats.get('triaged', 0)}"
        f" (high={priority_dist.get('high', 0)},"
        f" medium={priority_dist.get('medium', 0)},"
        f" low={priority_dist.get('low', 0)})",
        f"- **Build candidates:** {stats.get('build_candidates', 0)}",
        f"- **Research candidates:** {stats.get('research_candidates', 0)}",
        f"- **Researched:** {stats.get('researched', 0)}",
        f"- **Fully analyzed:** {stats['analyzed']}",
        "",
    ]

    # INVEST Candidates section (from deep analysis scores)
    lines += [
        "## INVEST Candidates (invest_score >= 8)",
        "",
    ]
    if invest_candidates:
        for a in invest_candidates:
            invest_rationale = _extract_section(a["content"], "Invest Score")
            risks_text = _extract_section(a["content"], "Risks")
            first_risk = ""
            for risk_line in risks_text.split("\n"):
                stripped = risk_line.strip("- ").strip()
                if stripped and stripped != "N/A":
                    first_risk = stripped
                    break

            lines += [
                f"### {a['name']} -- {a['invest_total']}/10",
                f"**Round:** {a['round_raw']} | **Category:** {a['category']}",
                f"**URL:** {a['url']}",
                "",
            ]
            if invest_rationale:
                lines.append(invest_rationale[:500])
            if first_risk:
                lines.append(f"**Key Risk:** {first_risk}")
            lines.append("")
    else:
        lines += ["No INVEST candidates this week.", ""]

    # WATCH List section
    lines += [
        "## WATCH List (score 6-7.9)",
        "",
        "| Name | Score | Category | Round | One-liner |",
        "|------|-------|----------|-------|-----------|",
    ]
    if watch_list:
        for a in watch_list:
            one_liner = _extract_section(a["content"], "One-liner") or ""
            one_liner = one_liner.replace("\n", " ").strip()[:100]
            name_col = a["name"].replace("|", "/")
            cat_col = str(a["category"]).replace("|", "/")
            round_col = str(a["round_raw"]).replace("|", "/")
            lines.append(
                f"| {name_col} | {a['invest_total']} | {cat_col}"
                f" | {round_col} | {one_liner} |"
            )
    else:
        lines.append("| (none this week) | -- | -- | -- | -- |")
    lines.append("")

    # BUILD Opportunities section (from deep analysis scores)
    lines += [
        "## BUILD Opportunities (build_score >= 8)",
        "",
    ]
    if build_opps:
        for a in build_opps:
            cis_section = _extract_section(a["content"], "CIS Adaptation")
            lines += [
                f"### {a['name']} -- Build Score: {a['build_total']}/10",
                f"**Category:** {a['category']} | **Round:** {a['round_raw']}",
                "",
            ]
            if cis_section:
                lines.append(f"**CIS Adaptation:** {cis_section[:300]}")
            lines.append("")
    else:
        lines += ["No BUILD opportunities this week.", ""]

    # Trends section
    lines += ["## Trends This Week", ""]
    if analyses:
        from collections import Counter
        category_counts = Counter(a["category"] for a in analyses if a.get("category"))
        top_categories = category_counts.most_common(5)
        for cat, count in top_categories:
            lines.append(f"- **{cat}**: {count} startup(s)")
    else:
        lines.append("- No analysis data available yet.")
    lines.append("")

    # All Analyzed Startups table
    lines += [
        "## All Analyzed Startups",
        "",
        "| Name | Invest | Build | Category | Round | Invest Verdict | Build Verdict |",
        "|------|--------|-------|----------|-------|----------------|---------------|",
    ]
    if analyses:
        for a in analyses:
            name_col = a["name"].replace("|", "/")
            cat_col = str(a["category"]).replace("|", "/")
            round_col = str(a["round_raw"]).replace("|", "/")
            lines.append(
                f"| {name_col} | {a['invest_total']} | {a['build_total']}"
                f" | {cat_col} | {round_col}"
                f" | {a['invest_verdict']} | {a['build_verdict']} |"
            )
    else:
        lines.append("| (no analyzed startups yet) | -- | -- | -- | -- | -- | -- |")
    lines.append("")

    return "\n".join(lines)


async def generate_digest_with_llm(data_json: str) -> str:
    """Try to generate the digest using the LLM. Returns markdown string."""
    prompt_template = load_prompt("digest")
    prompt = prompt_template.replace("{analysis_data}", data_json)

    # Only call LLM if dataset is manageable
    try:
        data = json.loads(data_json)
        analysis_count = len(data.get("analyses", []))
    except Exception:
        analysis_count = 0

    if analysis_count < 50:
        try:
            result = await call_llm(
                prompt,
                model=os.getenv("OPENROUTER_MODEL_LIGHT"),
                json_mode=False,
                temperature=0.3,
            )
            if isinstance(result, str):
                return result
        except Exception as e:
            log.warning("LLM digest generation failed: %s — falling back to manual template", e)

    return ""


async def run_digest() -> dict:
    """Main entry point: generate and save the weekly digest."""
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)

    stats = collect_pipeline_stats()
    analyses = collect_analyses()

    if not analyses:
        log.warning("no analysis files found in 3_analysis/ — generating minimal digest")

    # Try LLM generation first
    digest_md = ""
    if analyses:
        data_json = build_digest_data(stats, analyses)
        digest_md = await generate_digest_with_llm(data_json)

    # Fall back to manual template if LLM result is missing or too short
    if not digest_md or len(digest_md) < 200:
        digest_md = build_digest_manually(stats, analyses)

    # Generate filename: {YYYY}-W{WW}_weekly.md
    today = datetime.date.today()
    week_num = today.isocalendar()[1]
    filename = f"{today.year}-W{week_num:02d}_weekly.md"
    output_path = DIGESTS_DIR / filename

    output_path.write_text(digest_md, encoding="utf-8")
    log.info("Digest saved to %s", output_path)

    return {
        "digest_path": str(output_path),
        "stats": stats,
        "analysis_count": len(analyses),
    }


if __name__ == "__main__":
    asyncio.run(run_digest())

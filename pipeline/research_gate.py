import asyncio
import logging
import os
from pathlib import Path

import frontmatter
import yaml

from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, save_idea, make_slug

log = logging.getLogger("pipeline.research_gate")

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")
CONFIG_PATH = Path("config/triage.yaml")

REQUIRED_KEYS = {
    "has_team_data",
    "has_traction_data",
    "has_competitive_context",
    "ru_gap_detected",
    "oss_commercializable",
    "cross_sell_fit",
    "underserved_niche",
    "clear_localization_path",
}

# Fallback: all False when LLM fails
FALLBACK_RESULT = {key: False for key in REQUIRED_KEYS}


def _coerce_bool(value) -> bool:
    """Coerce various LLM response formats to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("yes", "true", "1")
    return bool(value)


async def evaluate_one(
    slug: str,
    research_dir: Path,
    idea_post: frontmatter.Post,
    prompt_template: str,
) -> dict:
    """Evaluate one startup's research data for analysis readiness.

    Returns dict with 8 boolean fields. Returns fallback (all False) on failure.
    """
    # Load research files
    website_path = research_dir / "website.md"
    research_path = research_dir / "web_research.md"

    website_content = ""
    if website_path.exists():
        website_content = website_path.read_text(encoding="utf-8")

    research_notes = ""
    if research_path.exists():
        research_notes = research_path.read_text(encoding="utf-8")

    name = idea_post.get("name", slug)
    url = idea_post.get("url", "")
    round_raw = idea_post.get("round_raw", "Unknown")
    sector = idea_post.get("sector", "unknown")
    description = idea_post.content or ""

    prompt = (
        prompt_template
        .replace("{name}", str(name))
        .replace("{url}", str(url))
        .replace("{round_raw}", str(round_raw))
        .replace("{sector}", str(sector))
        .replace("{description}", str(description))
        .replace("{website_content}", website_content[:3000])
        .replace("{research_notes}", research_notes[:3000])
    )

    result = await call_llm(
        prompt,
        model=os.getenv("OPENROUTER_MODEL_LIGHT"),
        json_mode=True,
    )

    if isinstance(result, Exception) or result is None or not isinstance(result, dict):
        log.warning("Research gate LLM failed for %s, using fallback (all False)", slug)
        return dict(FALLBACK_RESULT)

    if not REQUIRED_KEYS.issubset(result.keys()):
        missing = REQUIRED_KEYS - result.keys()
        log.warning("Missing keys for %s: %s, using fallback for missing", slug, missing)
        # Fill missing keys with False
        for key in missing:
            result[key] = False

    # Coerce all values to bool
    for key in REQUIRED_KEYS:
        result[key] = _coerce_bool(result.get(key, False))

    return result


def compute_analysis_ready(gate_result: dict, config: dict) -> bool:
    """Decide if startup has enough evidence for expensive deep analysis.

    Ready if: invest evidence >= threshold OR any rare build signal.
    """
    invest_evidence = sum([
        gate_result.get("has_team_data", False),
        gate_result.get("has_traction_data", False),
        gate_result.get("has_competitive_context", False),
    ])
    invest_ready = invest_evidence >= config["research_gate"]["invest_evidence_threshold"]

    rare_signals = config["research_gate"]["build_rare_signals"]
    build_ready = any(gate_result.get(sig, False) for sig in rare_signals)

    return invest_ready or build_ready


def compute_build_priority(gate_result: dict, config: dict) -> str:
    """Determine build priority from rare signal presence.

    Any rare signal = high, else medium (build_candidate was already true).
    """
    rare_signals = config["research_gate"]["build_rare_signals"]
    has_rare = any(gate_result.get(sig, False) for sig in rare_signals)
    if has_rare:
        return "high"
    return "medium"


async def run_research_gate() -> dict:
    """Run research gate on all researched startups.

    Evaluates enriched data to decide which startups are analysis-ready.
    Detects rare build signals only visible after research.
    """
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    prompt_template = load_prompt("research_gate")

    # Find all researched startups (have web_research.md)
    if not RESEARCH_DIR.exists():
        print("Research gate: no 2_research/ directory found")
        return {"ready": 0, "filtered": 0, "analysis_ready_slugs": []}

    research_slugs = [
        d.name
        for d in sorted(RESEARCH_DIR.iterdir())
        if d.is_dir() and (d / "web_research.md").exists()
    ]

    if not research_slugs:
        print("Research gate: no researched startups found")
        return {"ready": 0, "filtered": 0, "analysis_ready_slugs": []}

    # Build slug-to-idea mapping
    idea_map = {}
    for idea_file in sorted(IDEAS_DIR.glob("*.md")):
        try:
            post = load_idea(idea_file)
            slug = make_slug(post.get("name", ""))
            idea_map[slug] = (idea_file, post)
        except Exception:
            continue

    # Evaluate each researched startup
    eval_tasks = []
    eval_slugs = []

    for slug in research_slugs:
        research_dir = RESEARCH_DIR / slug
        idea_file, idea_post = idea_map.get(slug, (None, None))

        if idea_post is None:
            # Create minimal stub so evaluation can proceed
            idea_post = frontmatter.Post("", name=slug, url="")
            idea_file = None

        eval_tasks.append(evaluate_one(slug, research_dir, idea_post, prompt_template))
        eval_slugs.append((slug, idea_file, idea_post))

    results = await asyncio.gather(*eval_tasks, return_exceptions=True)

    ready_count = 0
    filtered_count = 0
    rare_count = 0
    analysis_ready_slugs = []

    for (slug, idea_file, idea_post), result in zip(eval_slugs, results):
        if isinstance(result, Exception):
            log.error("Research gate failed for %s: %s", slug, result)
            result = dict(FALLBACK_RESULT)

        analysis_ready = compute_analysis_ready(result, config)
        build_priority = compute_build_priority(result, config)

        # Write gate.md to 2_research/{slug}/
        gate_lines = [
            f"# Research Gate: {idea_post.get('name', slug)}",
            "",
            "## Invest Evidence",
            f"- has_team_data: {result.get('has_team_data', False)}",
            f"- has_traction_data: {result.get('has_traction_data', False)}",
            f"- has_competitive_context: {result.get('has_competitive_context', False)}",
            "",
            "## Build Signals",
            f"- ru_gap_detected: {result.get('ru_gap_detected', False)}",
            f"- oss_commercializable: {result.get('oss_commercializable', False)}",
            f"- cross_sell_fit: {result.get('cross_sell_fit', False)}",
            f"- underserved_niche: {result.get('underserved_niche', False)}",
            f"- clear_localization_path: {result.get('clear_localization_path', False)}",
            "",
            "## Decision",
            f"- analysis_ready: {analysis_ready}",
            f"- build_priority: {build_priority}",
        ]
        gate_path = RESEARCH_DIR / slug / "gate.md"
        gate_path.write_text("\n".join(gate_lines), encoding="utf-8")

        # Update idea frontmatter if we have the file
        if idea_file is not None:
            idea_post["analysis_ready"] = analysis_ready
            idea_post["build_priority"] = build_priority
            for key in REQUIRED_KEYS:
                idea_post[key] = result.get(key, False)
            save_idea(idea_post, idea_file)

        if analysis_ready:
            ready_count += 1
            analysis_ready_slugs.append(slug)
        else:
            filtered_count += 1

        # Count rare signals
        rare_signals = config["research_gate"]["build_rare_signals"]
        if any(result.get(sig, False) for sig in rare_signals):
            rare_count += 1

    print(
        f"Research gate: {ready_count} analysis-ready, "
        f"{filtered_count} filtered out, "
        f"{rare_count} with rare build signals"
    )

    return {
        "ready": ready_count,
        "filtered": filtered_count,
        "rare_signals": rare_count,
        "analysis_ready_slugs": analysis_ready_slugs,
    }


if __name__ == "__main__":
    asyncio.run(run_research_gate())

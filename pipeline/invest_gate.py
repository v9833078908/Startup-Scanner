import asyncio
import logging
import os
from pathlib import Path

import frontmatter
import yaml

from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, save_idea, make_slug

log = logging.getLogger("pipeline.invest_gate")

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")
CONFIG_PATH = Path("config/triage.yaml")

REQUIRED_KEYS = {"has_team_data", "has_traction_data", "has_competitive_context"}
FALLBACK_RESULT = {key: False for key in REQUIRED_KEYS}


def _coerce_bool(value) -> bool:
    """Coerce various LLM response formats to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("yes", "true", "1")
    return bool(value)


async def evaluate_invest(
    slug: str,
    research_dir: Path,
    idea_post: frontmatter.Post,
    prompt_template: str,
) -> dict:
    """Evaluate invest research for analysis readiness.

    Returns dict with 3 boolean fields. Returns fallback (all False) on failure.
    """
    # Load invest_research.md (NOT web_research.md)
    invest_research_path = research_dir / "invest_research.md"
    invest_notes = ""
    if invest_research_path.exists():
        invest_notes = invest_research_path.read_text(encoding="utf-8")

    # Also load website.md
    website_path = research_dir / "website.md"
    website_content = ""
    if website_path.exists():
        website_content = website_path.read_text(encoding="utf-8")

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
        .replace("{description}", str(description)[:2000])
        .replace("{website_content}", website_content[:3000])
        .replace("{invest_research_notes}", invest_notes[:3000])
    )

    result = await call_llm(
        prompt,
        model=os.getenv("OPENROUTER_MODEL_MEDIUM"),
        json_mode=True,
    )

    if isinstance(result, Exception) or result is None or not isinstance(result, dict):
        log.warning("Invest gate LLM failed for %s, using fallback (all False)", slug)
        return dict(FALLBACK_RESULT)

    # Fill missing keys with False
    for key in REQUIRED_KEYS:
        if key not in result:
            log.warning("Missing key %s for %s, defaulting to False", key, slug)
            result[key] = False

    # Coerce all values to bool
    for key in REQUIRED_KEYS:
        result[key] = _coerce_bool(result.get(key, False))

    return result


def compute_invest_ready(gate_result: dict, config: dict) -> bool:
    """Ready if invest evidence >= threshold (2/3)."""
    evidence = sum(gate_result.get(k, False) for k in REQUIRED_KEYS)
    return evidence >= config["research_gate"]["invest_evidence_threshold"]


async def run_invest_gate(slugs: list[str]) -> dict:
    """Run invest gate on invest-researched startups.

    Evaluates Exa-based invest research to decide analysis readiness.
    Writes gate_invest.md to 2_research/{slug}/.
    Updates idea frontmatter with invest_analysis_ready and evidence fields.
    """
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    prompt_template = load_prompt("invest_gate")

    # Build slug-to-idea mapping
    idea_map = {}
    for idea_file in sorted(IDEAS_DIR.glob("*.md")):
        try:
            post = load_idea(idea_file)
            file_slug = make_slug(post.get("name", ""))
            idea_map[file_slug] = (idea_file, post)
        except Exception:
            continue

    eval_tasks = []
    eval_slugs = []

    for slug in slugs:
        research_dir = RESEARCH_DIR / slug
        if not (research_dir / "invest_research.md").exists():
            log.info("Skipping %s: no invest_research.md", slug)
            continue

        idea_file, idea_post = idea_map.get(slug, (None, None))
        if idea_post is None:
            idea_post = frontmatter.Post("", name=slug, url="")
            idea_file = None

        eval_tasks.append(evaluate_invest(slug, research_dir, idea_post, prompt_template))
        eval_slugs.append((slug, idea_file, idea_post))

    results = await asyncio.gather(*eval_tasks, return_exceptions=True)

    ready_count = 0
    filtered_count = 0
    invest_analysis_ready_slugs = []

    for (slug, idea_file, idea_post), result in zip(eval_slugs, results):
        if isinstance(result, Exception):
            log.error("Invest gate failed for %s: %s", slug, result)
            result = dict(FALLBACK_RESULT)

        invest_ready = compute_invest_ready(result, config)

        # Write gate_invest.md
        gate_lines = [
            f"# Invest Gate: {idea_post.get('name', slug)}",
            "",
            "## Invest Evidence",
            f"- has_team_data: {result.get('has_team_data', False)}",
            f"- has_traction_data: {result.get('has_traction_data', False)}",
            f"- has_competitive_context: {result.get('has_competitive_context', False)}",
            "",
            "## Decision",
            f"- invest_analysis_ready: {invest_ready}",
        ]
        gate_path = RESEARCH_DIR / slug / "gate_invest.md"
        gate_path.write_text("\n".join(gate_lines), encoding="utf-8")

        # Update idea frontmatter
        if idea_file is not None:
            idea_post["invest_analysis_ready"] = invest_ready
            for key in REQUIRED_KEYS:
                idea_post[key] = result.get(key, False)
            save_idea(idea_post, idea_file)

        if invest_ready:
            ready_count += 1
            invest_analysis_ready_slugs.append(slug)
        else:
            filtered_count += 1

    log.info(
        "Invest gate: %d analysis-ready, %d filtered",
        ready_count, filtered_count,
    )

    return {
        "ready": ready_count,
        "filtered": filtered_count,
        "invest_analysis_ready_slugs": invest_analysis_ready_slugs,
    }


if __name__ == "__main__":
    asyncio.run(run_invest_gate([]))

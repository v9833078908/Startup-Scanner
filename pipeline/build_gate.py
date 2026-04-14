import asyncio
import json
import logging
import os
from pathlib import Path

import frontmatter
import yaml

from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, save_idea, make_slug

# If DEMAND_SIGNAL bucket returned >= this many RU landing pages, the gate
# mechanically forces cis_gap_confirmed=False regardless of LLM judgement.
RU_LANDING_OVERRIDE_THRESHOLD = 3

log = logging.getLogger("pipeline.build_gate")

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")
CONFIG_PATH = Path("config/triage.yaml")

REQUIRED_KEYS = {
    "cis_gap_confirmed",
    "replicable_confirmed",
    "oss_base_available",
    "market_demand_signals",
    "clear_localization_path",
}
FALLBACK_RESULT = {key: False for key in REQUIRED_KEYS}


def _coerce_bool(value) -> bool:
    """Coerce various LLM response formats to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("yes", "true", "1")
    return bool(value)


async def evaluate_build(
    slug: str,
    research_dir: Path,
    idea_post: frontmatter.Post,
    prompt_template: str,
) -> dict:
    """Evaluate build research for analysis readiness.

    Returns dict with 5 boolean fields. Returns fallback (all False) on failure.
    """
    # Load build_research.md
    build_research_path = research_dir / "build_research.md"
    build_notes = ""
    if build_research_path.exists():
        build_notes = build_research_path.read_text(encoding="utf-8")

    name = idea_post.get("name", slug)
    category = idea_post.get("category", idea_post.get("sector", "technology"))
    description = idea_post.content or ""

    prompt = (
        prompt_template
        .replace("{name}", str(name))
        .replace("{category}", str(category))
        .replace("{description}", str(description)[:2000])
        .replace("{build_research_notes}", build_notes[:3000])
    )

    result = await call_llm(
        prompt,
        model=os.getenv("OPENROUTER_MODEL_MEDIUM"),
        json_mode=True,
    )

    if isinstance(result, Exception) or result is None or not isinstance(result, dict):
        log.warning("Build gate LLM failed for %s, using fallback (all False)", slug)
        return dict(FALLBACK_RESULT)

    # Fill missing keys with False
    for key in REQUIRED_KEYS:
        if key not in result:
            log.warning("Missing key %s for %s, defaulting to False", key, slug)
            result[key] = False

    # Coerce all values to bool
    for key in REQUIRED_KEYS:
        result[key] = _coerce_bool(result.get(key, False))

    # Mechanical override: ≥3 RU landing pages for "купить {category}" means
    # local commercial supply exists — cis_gap_confirmed cannot be true.
    raw_path = research_dir / "build_research_raw.json"
    if raw_path.exists():
        try:
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            ru_hits = (
                raw.get("buckets", {})
                .get("DEMAND_SIGNAL", {})
                .get("ru_landing_count", 0)
            )
            if ru_hits >= RU_LANDING_OVERRIDE_THRESHOLD and result.get("cis_gap_confirmed"):
                log.info(
                    "Build gate override for %s: %d RU landings → cis_gap_confirmed=False",
                    slug, ru_hits,
                )
                result["cis_gap_confirmed"] = False
                result["_override"] = f"demand_signal_ru_landings={ru_hits}"
        except Exception as exc:
            log.warning("Override check failed for %s: %s", slug, exc)

    return result


def compute_build_ready(gate_result: dict, config: dict = None) -> bool:
    """Ready if cis_gap_confirmed OR (replicable_confirmed AND market_demand_signals)."""
    return (
        gate_result.get("cis_gap_confirmed", False)
        or (
            gate_result.get("replicable_confirmed", False)
            and gate_result.get("market_demand_signals", False)
        )
    )


def compute_build_priority(gate_result: dict) -> str:
    """High if oss_base_available (head start), else medium."""
    if gate_result.get("oss_base_available", False):
        return "high"
    return "medium"


async def run_build_gate(slugs: list[str]) -> dict:
    """Run build gate on build-researched startups.

    Evaluates Exa-based build research to decide analysis readiness.
    Writes gate_build.md to 2_research/{slug}/.
    Updates idea frontmatter with build_analysis_ready, build_priority, and signal fields.
    """
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    prompt_template = load_prompt("build_gate")

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
        if not (research_dir / "build_research.md").exists():
            log.info("Skipping %s: no build_research.md", slug)
            continue

        idea_file, idea_post = idea_map.get(slug, (None, None))
        if idea_post is None:
            idea_post = frontmatter.Post("", name=slug, url="")
            idea_file = None

        eval_tasks.append(evaluate_build(slug, research_dir, idea_post, prompt_template))
        eval_slugs.append((slug, idea_file, idea_post))

    results = await asyncio.gather(*eval_tasks, return_exceptions=True)

    ready_count = 0
    filtered_count = 0
    build_analysis_ready_slugs = []

    for (slug, idea_file, idea_post), result in zip(eval_slugs, results):
        if isinstance(result, Exception):
            log.error("Build gate failed for %s: %s", slug, result)
            result = dict(FALLBACK_RESULT)

        build_ready = compute_build_ready(result, config)
        build_priority = compute_build_priority(result)

        # Write gate_build.md
        override_suffix = (
            f"  (override: {result['_override']})" if result.get("_override") else ""
        )
        gate_lines = [
            f"# Build Gate: {idea_post.get('name', slug)}",
            "",
            "## Build Signals",
            f"- cis_gap_confirmed: {result.get('cis_gap_confirmed', False)}{override_suffix}",
            f"- replicable_confirmed: {result.get('replicable_confirmed', False)}",
            f"- oss_base_available: {result.get('oss_base_available', False)}",
            f"- market_demand_signals: {result.get('market_demand_signals', False)}",
            f"- clear_localization_path: {result.get('clear_localization_path', False)}",
            "",
            "## Decision",
            f"- build_analysis_ready: {build_ready}",
            f"- build_priority: {build_priority}",
        ]
        gate_path = RESEARCH_DIR / slug / "gate_build.md"
        gate_path.write_text("\n".join(gate_lines), encoding="utf-8")

        # Update idea frontmatter
        if idea_file is not None:
            idea_post["build_analysis_ready"] = build_ready
            idea_post["build_priority"] = build_priority
            for key in REQUIRED_KEYS:
                idea_post[key] = result.get(key, False)
            save_idea(idea_post, idea_file)

        if build_ready:
            ready_count += 1
            build_analysis_ready_slugs.append(slug)
        else:
            filtered_count += 1

    log.info(
        "Build gate: %d analysis-ready, %d filtered",
        ready_count, filtered_count,
    )

    return {
        "ready": ready_count,
        "filtered": filtered_count,
        "build_analysis_ready_slugs": build_analysis_ready_slugs,
    }


if __name__ == "__main__":
    asyncio.run(run_build_gate([]))

import asyncio
import json
import logging
import os
from collections import defaultdict
from pathlib import Path

import frontmatter
import yaml

from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, save_idea, make_slug

log = logging.getLogger("pipeline.triage")

IDEAS_DIR = Path("1_ideas")
CONFIG_PATH = Path("config/triage.yaml")

REQUIRED_KEYS = {
    "has_product_evidence",
    "barriers",
    "one_liner",
    "category",
    "replicability",
    "cis_gap_likelihood",
    "stack_fit",
    "build_thesis",
}

# Fields that come from the triage LLM result (not idea frontmatter).
# Used by evaluate_build_candidate to know where to read each rule's value from.
TRIAGE_RESULT_FIELDS = {
    "replicability",
    "stack_fit",
    "cis_gap_likelihood",
    "has_product_evidence",
}


def load_triage_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def is_round_in_range(round_usd: int | None) -> bool:
    """Check if round is in iFree's extended range ($30K-$2M)."""
    if round_usd is None:
        return False
    return 30_000 <= round_usd <= 2_000_000


def _coerce_bool(value) -> bool:
    """Coerce various LLM response formats to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("yes", "true", "1")
    return bool(value)


async def triage_one(post: frontmatter.Post, prompt_template: str) -> dict | None:
    """Ask LLM binary evidence questions about a startup.

    Returns dict with has_product_evidence, barriers, one_liner, category,
    replicability, cis_gap_likelihood, stack_fit. Returns None on failure.
    """
    name = post.get("name", "Unknown")
    url = post.get("url", "")
    round_raw = post.get("round_raw", "Unknown")
    description = post.content or ""
    sector = post.get("sector", "unknown")
    product_type = post.get("product_type", "unknown")

    prompt = (
        prompt_template
        .replace("{name}", str(name))
        .replace("{url}", str(url))
        .replace("{round_raw}", str(round_raw))
        .replace("{description}", str(description))
        .replace("{sector}", str(sector))
        .replace("{product_type}", str(product_type))
    )

    result = await call_llm(
        prompt,
        model=os.getenv("OPENROUTER_MODEL_LIGHT"),
        json_mode=True,
        temperature=0.0,
    )

    if isinstance(result, Exception) or result is None:
        return None

    if not isinstance(result, dict):
        return None

    if not REQUIRED_KEYS.issubset(result.keys()):
        log.warning("Missing keys in triage result: %s", REQUIRED_KEYS - result.keys())
        return None

    # Coerce boolean fields
    result["has_product_evidence"] = _coerce_bool(result["has_product_evidence"])
    result["cis_gap_likelihood"] = _coerce_bool(result.get("cis_gap_likelihood", False))
    result["stack_fit"] = _coerce_bool(result.get("stack_fit", False))

    # Validate replicability
    valid_repl = ("easy", "medium", "hard", "impossible")
    repl = str(result.get("replicability", "hard")).lower()
    result["replicability"] = repl if repl in valid_repl else "hard"

    return result


def compute_invest_priority(
    post: frontmatter.Post, triage_result: dict, config: dict
) -> str:
    """Count binary yes signals to determine invest priority.

    3 signals: sector_fit, round_in_range, has_product_evidence.
    (has_founder_signal removed — DealPad almost never contains founder data.)
    Founder evaluation deferred to research/analysis stages where evidence exists.
    """
    sector_fit = post.get("sector_match") in ("yes", "partial")
    round_in_range = is_round_in_range(post.get("round_usd"))
    has_product = triage_result.get("has_product_evidence", False)

    signal_count = sum([sector_fit, round_in_range, has_product])

    thresholds = config["invest_priority_thresholds"]
    if signal_count >= thresholds["high"]:
        return "high"
    if signal_count >= thresholds["medium"]:
        return "medium"
    return "low"


def evaluate_build_candidate(
    post: frontmatter.Post, triage_result: dict, config: dict
) -> tuple[bool, list[str]]:
    """Declarative evaluation of build_candidate_requires.

    Iterates over every rule in config['build_candidate_requires']:
    - list value → membership check
    - bool value → coerced equality
    - scalar value → direct equality

    Source of value: triage_result for TRIAGE_RESULT_FIELDS, otherwise post (frontmatter).

    Returns (is_candidate, failed_rules). failed_rules is empty if candidate.
    """
    req = config["build_candidate_requires"]
    failed: list[str] = []

    for field, expected in req.items():
        if field in TRIAGE_RESULT_FIELDS:
            actual = triage_result.get(field)
        else:
            actual = post.get(field)

        if isinstance(expected, list):
            ok = actual in expected
        elif isinstance(expected, bool):
            ok = _coerce_bool(actual) == expected
        else:
            ok = actual == expected

        if not ok:
            failed.append(field)

    return (len(failed) == 0, failed)


def compute_route(invest_priority: str, build_candidate: bool) -> str:
    """Determine pipeline track from invest priority and build candidate status."""
    invest_interested = invest_priority in ("high", "medium")
    if invest_interested and build_candidate:
        return "both"
    if invest_interested:
        return "invest"
    if build_candidate:
        return "build"
    return "skip"


async def run_triage() -> dict:
    """Run triage on all pre-filtered ideas.

    Replaces quick_score: produces invest_priority (high/medium/low)
    and build_candidate (bool), NOT invest_score/build_score.
    """
    config = load_triage_config()
    prompt_template = load_prompt("triage")

    all_files = sorted(IDEAS_DIR.glob("*.md"))

    to_triage = []
    skipped = 0

    for file_path in all_files:
        post = load_idea(file_path)
        if post.get("filtered") != "passed":
            continue
        if "invest_priority" in post.metadata:
            skipped += 1
            continue
        to_triage.append((file_path, post))

    tasks = [triage_one(post, prompt_template) for _, post in to_triage]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    triaged_count = 0
    failed_count = 0
    priority_dist = {"high": 0, "medium": 0, "low": 0}
    route_dist = {"invest": 0, "build": 0, "both": 0, "skip": 0}
    build_count = 0
    rejection_counts: dict[str, int] = defaultdict(int)
    research_list = []

    for (file_path, post), result in zip(to_triage, results):
        if isinstance(result, Exception) or result is None:
            failed_count += 1
            continue

        invest_priority = compute_invest_priority(post, result, config)
        build_candidate, failed_rules = evaluate_build_candidate(post, result, config)
        route = compute_route(invest_priority, build_candidate)

        # Write triage fields to frontmatter
        post["invest_priority"] = invest_priority
        post["build_candidate"] = build_candidate
        post["has_product_evidence"] = result["has_product_evidence"]
        post["barriers"] = result.get("barriers", [])
        post["one_liner"] = result.get("one_liner")
        post["category"] = result.get("category")
        post["replicability"] = result["replicability"]
        post["cis_gap_likelihood"] = result["cis_gap_likelihood"]
        post["stack_fit"] = result["stack_fit"]
        post["build_thesis"] = result.get("build_thesis")
        post["route"] = route
        if not build_candidate:
            post["build_reject_reasons"] = failed_rules
            for rule in failed_rules:
                rejection_counts[rule] += 1

        save_idea(post, file_path)
        triaged_count += 1

        priority_dist[invest_priority] += 1
        route_dist[route] += 1
        if build_candidate:
            build_count += 1

        # Research list: anything worth investigating further
        if route != "skip":
            slug = make_slug(post.get("name", file_path.stem))
            research_list.append(slug)

    # Also include previously triaged ideas in research list
    for file_path in all_files:
        post = load_idea(file_path)
        if post.get("filtered") != "passed":
            continue
        slug = make_slug(post.get("name", file_path.stem))
        if slug in research_list:
            continue
        r = post.get("route", "skip")
        if r != "skip":
            research_list.append(slug)

    rejection_summary = ", ".join(
        f"{k}={v}" for k, v in sorted(rejection_counts.items(), key=lambda x: -x[1])
    ) or "none"

    print(
        f"Triage: {triaged_count} triaged, {failed_count} failed, {skipped} skipped\n"
        f"  Priority: high={priority_dist['high']}, medium={priority_dist['medium']}, "
        f"low={priority_dist['low']}\n"
        f"  Route: invest={route_dist['invest']}, build={route_dist['build']}, "
        f"both={route_dist['both']}, skip={route_dist['skip']}\n"
        f"  Build candidates: {build_count}\n"
        f"  Build rejections by rule: {rejection_summary}\n"
        f"  Research list: {len(research_list)} ideas"
    )

    return {
        "triaged": triaged_count,
        "failed": failed_count,
        "skipped": skipped,
        "priority_distribution": priority_dist,
        "route_distribution": route_dist,
        "build_candidates": build_count,
        "rejection_counts": dict(rejection_counts),
        "research_list": research_list,
        "research_count": len(research_list),
    }


if __name__ == "__main__":
    asyncio.run(run_triage())

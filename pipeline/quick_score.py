import asyncio
import os
from pathlib import Path

import frontmatter
import yaml

from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, save_idea

IDEAS_DIR = Path("1_ideas")
FORMULA_PATH = Path("config/scoring_formula.yaml")

REQUIRED_KEYS = {
    "has_product_signal",
    "founder_signal",
    "cis_transferable",
    "uniqueness",
    "market_potential",
    "one_liner",
    "category",
    "invest_rationale",
    "build_rationale",
}


def load_formula() -> dict:
    return yaml.safe_load(FORMULA_PATH.read_text(encoding="utf-8"))


def compute_round_fit(round_usd: int | None) -> str:
    """
    Map round_usd to a fit category relative to iFree check size ($30K-$300K).

    This is a SCORING FACTOR, not an eligibility gate.
    """
    if round_usd is None:
        return "far"
    if 30_000 <= round_usd <= 300_000:
        return "in_range"   # ideal iFree check size
    if 300_000 < round_usd <= 2_000_000:
        return "close"      # early stage, possible
    return "far"            # too small or too large — not disqualifying


def compute_score(answers: dict, formula: dict) -> int:
    """
    Compute a score from structured answers using formula weights.

    Returns integer clamped to [0, 10].
    """
    total = 0
    for factor_name, value_map in formula.items():
        answer_value = answers.get(factor_name, "unknown")
        if isinstance(answer_value, str):
            answer_value = answer_value.lower()
        points = value_map.get(answer_value, 0)
        total += points
    return max(0, min(10, total))


async def score_one_idea(post: frontmatter.Post, prompt_template: str) -> dict | None:
    """
    Ask LLM structured questions about a startup.

    Returns dict of answers or None on failure.
    LLM does NOT generate scores — those are computed by formula.
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
    )

    if isinstance(result, Exception) or result is None:
        return None

    if not isinstance(result, dict):
        return None

    if not REQUIRED_KEYS.issubset(result.keys()):
        return None

    return result


async def run_quick_score() -> dict:
    """
    Score all invest_eligible or build_eligible ideas using structured questions + formula.

    Scores are computed by formula from structured LLM answers — not LLM-generated numbers.
    Thresholds for shortlisting are read from config/scoring_formula.yaml.
    """
    formula = load_formula()
    prompt_template = load_prompt("quick_score")

    invest_threshold = formula["shortlist"]["invest_threshold"]
    build_threshold = formula["shortlist"]["build_threshold"]

    all_files = sorted(IDEAS_DIR.glob("*.md"))

    to_score = []
    skipped = 0

    for file_path in all_files:
        post = load_idea(file_path)
        if post.get("filtered") != "passed":
            continue
        if "invest_score" in post.metadata:
            skipped += 1
            continue
        to_score.append((file_path, post))

    tasks = [score_one_idea(post, prompt_template) for _, post in to_score]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scored_count = 0
    failed_count = 0

    for (file_path, post), result in zip(to_score, results):
        if isinstance(result, Exception) or result is None:
            failed_count += 1
            continue

        # Build answers dict by merging prefilter classification + LLM answers + mechanical
        answers = {
            # From prefilter classification
            "sector_match": post.get("sector_match", "partial"),
            "product_type": post.get("product_type", "unknown"),
            "b2b_b2c": post.get("b2b_b2c", "unknown"),
            # From LLM: has_product_signal maps to "has_product" key in formula
            "has_product": result.get("has_product_signal", "unknown"),
            "founder_signal": result.get("founder_signal", "unknown"),
            "cis_transferable": result.get("cis_transferable", "low"),
            "uniqueness": result.get("uniqueness", "incremental"),
            "market_potential": result.get("market_potential", "niche"),
            # Mechanical: round fit from round_usd
            "round_fit": compute_round_fit(post.get("round_usd")),
        }

        invest_score = compute_score(answers, formula["invest_formula"])
        build_score = compute_score(answers, formula["build_formula"])

        # Write all fields to frontmatter
        post["has_product_signal"] = result.get("has_product_signal")
        post["founder_signal"] = result.get("founder_signal")
        post["cis_transferable"] = result.get("cis_transferable")
        post["uniqueness"] = result.get("uniqueness")
        post["market_potential"] = result.get("market_potential")
        post["round_fit"] = answers["round_fit"]
        post["invest_score"] = invest_score
        post["build_score"] = build_score
        post["one_liner"] = result.get("one_liner")
        post["category"] = result.get("category")
        post["invest_rationale"] = result.get("invest_rationale")
        post["build_rationale"] = result.get("build_rationale")

        save_idea(post, file_path)
        scored_count += 1

    # Build shortlist by re-scanning all passed ideas (handles idempotent re-runs)
    shortlist = []
    for file_path in sorted(IDEAS_DIR.glob("*.md")):
        post = load_idea(file_path)
        if post.get("filtered") != "passed":
            continue
        invest = post.get("invest_score", 0) or 0
        build = post.get("build_score", 0) or 0
        if invest >= invest_threshold or build >= build_threshold:
            shortlist.append(str(file_path))

    print(
        f"Quick score: {scored_count} scored, {failed_count} failed, "
        f"{skipped} skipped, {len(shortlist)} shortlisted "
        f"(invest>={invest_threshold} OR build>={build_threshold})"
    )

    return {
        "scored": scored_count,
        "failed": failed_count,
        "skipped": skipped,
        "shortlist": shortlist,
        "shortlist_count": len(shortlist),
    }


if __name__ == "__main__":
    asyncio.run(run_quick_score())

import asyncio
import os
import re
import shutil
from pathlib import Path

import frontmatter
import yaml

from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, save_idea

IDEAS_DIR = Path("1_ideas")
ARCHIVE_DIR = Path("_archive")
FILTERS_PATH = Path("config/filters.yaml")


def load_filters() -> dict:
    return yaml.safe_load(FILTERS_PATH.read_text(encoding="utf-8"))


def hard_reject(post: frontmatter.Post, filters: dict) -> str | None:
    """
    Apply hard-reject criteria (no LLM needed).

    Returns rejection reason string or None if idea passes.
    """
    content = post.content or post.get("description", "")
    name = post.get("name", "")
    combined_text = content + " " + name

    # Check 1: description length
    min_len = filters.get("min_description_length", 20)
    if len(content.strip()) < min_len:
        return "description_too_short"

    # Check 2: exclude niches — word-boundary regex to avoid false matches
    exclude_niches = filters.get("exclude_niches", [])
    for keyword in exclude_niches:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, combined_text, re.IGNORECASE):
            return f"excluded_niche:{keyword}"

    # Check 3: round size hard reject (not startup territory)
    round_usd = post.get("round_usd")
    max_round = filters.get("max_round_usd")
    if round_usd is not None and max_round is not None and round_usd >= max_round:
        return "round_too_large"

    return None


async def classify_one(post: frontmatter.Post, prompt_template: str) -> dict:
    """
    Classify a startup via LLM along 5 dimensions.

    On any failure, returns a safe fallback dict with is_tech=True,
    sector_match='partial' so the idea passes through to scoring.
    Never returns None.
    """
    REQUIRED_KEYS = {"is_tech", "sector", "sector_match", "product_type", "b2b_b2c"}

    FALLBACK = {
        "is_tech": True,
        "sector": "unknown",
        "sector_match": "partial",
        "product_type": "unknown",
        "b2b_b2c": "unknown",
        "classification_status": "failed",
        "review_needed": True,
    }

    name = post.get("name", "Unknown")
    url = post.get("url", "")
    round_raw = post.get("round_raw", "Unknown")
    description = post.content or ""

    prompt = (
        prompt_template
        .replace("{name}", str(name))
        .replace("{url}", str(url))
        .replace("{round_raw}", str(round_raw))
        .replace("{description}", str(description))
    )

    try:
        result = await call_llm(
            prompt,
            model=os.getenv("OPENROUTER_MODEL_LIGHT"),
            json_mode=True,
        )

        if not isinstance(result, dict):
            return FALLBACK

        if not REQUIRED_KEYS.issubset(result.keys()):
            return FALLBACK

        return {**result, "classification_status": "classified"}

    except Exception:
        return FALLBACK


def compute_eligibility(post: frontmatter.Post) -> tuple[bool, bool]:
    """
    Compute invest_eligible and build_eligible from classification fields.

    NOTE: Round size is NOT used as eligibility gate — it's a scoring factor
    in quick_score formula (round_fit). We never reject on round here.
    """
    is_tech = post.get("is_tech") is True
    sector_match = post.get("sector_match", "no")
    product_type = post.get("product_type", "other")

    sector_ok = sector_match in ("yes", "partial")

    invest_eligible = is_tech and sector_ok

    # "unknown" product_type passes build — don't reject on classification failure
    build_product_ok = product_type in ("software", "service", "unknown")
    build_eligible = is_tech and sector_ok and build_product_ok

    return invest_eligible, build_eligible


async def run_prefilter() -> dict:
    """
    Two-stage pre-filter:
      Stage A — hard rejects (no LLM): description length, excluded niches, giant rounds
      Stage B — LLM classification: sector, product type, b2b/b2c
      Stage C — compute invest_eligible and build_eligible

    Graceful failure: LLM errors → classification_status='failed' + review_needed=True.
    Never archives classification failures — they pass through for human review.

    Idempotent: skips ideas that already have 'classification_status' in frontmatter.
    """
    filters = load_filters()
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    classify_prompt = load_prompt("classify")

    all_files = sorted(IDEAS_DIR.glob("*.md"))

    hard_rejected = 0
    to_classify = []
    already_done = 0

    # Stage A: hard rejects
    for file_path in all_files:
        post = load_idea(file_path)

        # Idempotency: skip already-processed ideas
        if "classification_status" in post.metadata:
            already_done += 1
            continue

        reason = hard_reject(post, filters)
        if reason is not None:
            post["filtered"] = "rejected"
            post["filter_reason"] = reason
            save_idea(post, file_path)
            shutil.move(str(file_path), str(ARCHIVE_DIR / file_path.name))
            hard_rejected += 1
        else:
            to_classify.append((file_path, post))

    # Stage B: LLM classification (async, concurrent)
    tasks = [classify_one(post, classify_prompt) for _, post in to_classify]
    classification_results = await asyncio.gather(*tasks, return_exceptions=True)

    failed_count = 0
    classified_count = 0
    archived_count = 0

    # Stage C: write classification, compute eligibility, archive only dual-ineligible non-failures
    for (file_path, post), result in zip(to_classify, classification_results):
        # Handle gather exceptions — use fallback
        if isinstance(result, Exception):
            result = {
                "is_tech": True,
                "sector": "unknown",
                "sector_match": "partial",
                "product_type": "unknown",
                "b2b_b2c": "unknown",
                "classification_status": "failed",
                "review_needed": True,
            }

        # Write classification fields to frontmatter
        post["is_tech"] = result.get("is_tech", True)
        post["sector"] = result.get("sector", "unknown")
        post["sector_match"] = result.get("sector_match", "partial")
        post["product_type"] = result.get("product_type", "unknown")
        post["b2b_b2c"] = result.get("b2b_b2c", "unknown")
        post["classification_status"] = result.get("classification_status", "failed")

        if result.get("review_needed"):
            post["review_needed"] = True
            failed_count += 1
        else:
            classified_count += 1

        # Compute eligibility
        invest_eligible, build_eligible = compute_eligibility(post)
        post["invest_eligible"] = invest_eligible
        post["build_eligible"] = build_eligible

        # Backward compat: filtered="passed" for downstream steps
        post["filtered"] = "passed"

        # Archive only truly ineligible ideas that were successfully classified
        # Never archive classification failures — they get review_needed instead
        if (not invest_eligible and not build_eligible
                and post["classification_status"] != "failed"):
            post["filtered"] = "rejected"
            post["filter_reason"] = "not_eligible_for_invest_or_build"
            save_idea(post, file_path)
            shutil.move(str(file_path), str(ARCHIVE_DIR / file_path.name))
            archived_count += 1
        else:
            save_idea(post, file_path)

    invest_eligible_count = 0
    build_eligible_count = 0
    for file_path in sorted(IDEAS_DIR.glob("*.md")):
        try:
            post = load_idea(file_path)
            if post.get("invest_eligible"):
                invest_eligible_count += 1
            if post.get("build_eligible"):
                build_eligible_count += 1
        except Exception:
            continue

    print(
        f"Pre-filter: {hard_rejected} hard rejected, {classified_count + failed_count} classified "
        f"({failed_count} LLM failures → review_needed), "
        f"{invest_eligible_count} invest-eligible, {build_eligible_count} build-eligible, "
        f"{archived_count} archived"
    )

    return {
        "hard_rejected": hard_rejected,
        "classified": classified_count,
        "failed": failed_count,
        "invest_eligible": invest_eligible_count,
        "build_eligible": build_eligible_count,
        "archived": archived_count,
        "skipped": already_done,
    }


if __name__ == "__main__":
    asyncio.run(run_prefilter())

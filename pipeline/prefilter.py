import re
import shutil
import sys
from pathlib import Path

import yaml
import frontmatter

from lib.utils import load_idea, save_idea

IDEAS_DIR = Path("1_ideas")
ARCHIVE_DIR = Path("_archive")
CONFIG_PATH = Path("config/filters.yaml")


def load_filters() -> dict:
    """Read and return the filters.yaml config as a dict."""
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def matches_niches(text: str, niches: list[str]) -> bool:
    """
    Return True if text contains any keyword from niches as a whole word.

    Uses word-boundary regex to avoid 'AI' matching 'rail', 'wait', 'detail', etc.
    (Pitfall 5 from RESEARCH.md)
    """
    for keyword in niches:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def check_filters(post: frontmatter.Post, filters: dict) -> str | None:
    """
    Apply filter criteria to a parsed idea Post.

    Returns a rejection reason string if rejected, or None if the idea passes.
    """
    content = post.content or post.get("description", "")
    name = post.get("name", "")
    combined_text = content + " " + name

    # Check 1: description length
    min_len = filters.get("min_description_length", 20)
    if len(content.strip()) < min_len:
        return "description_too_short"

    # Check 2: exclude niches — reject if any excluded keyword matches
    exclude_niches = filters.get("exclude_niches", [])
    if exclude_niches and matches_niches(combined_text, exclude_niches):
        # Find the matched keyword to include in the reason
        for keyword in exclude_niches:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, combined_text, re.IGNORECASE):
                return f"excluded_niche:{keyword}"

    # Check 3: include niches — reject if none of the included niches match
    include_niches = filters.get("include_niches", [])
    if include_niches and not matches_niches(combined_text, include_niches):
        return "no_matching_niche"

    # Check 4: round size filters
    round_usd = post.get("round_usd")
    if round_usd is not None:
        min_round = filters.get("min_round_usd")
        max_round = filters.get("max_round_usd")
        if min_round and round_usd < min_round:
            return "round_too_small"
        if max_round and round_usd > max_round:
            return "round_too_large"

    return None


def run_prefilter() -> dict:
    """
    Read all .md files from 1_ideas/, apply filters.yaml, archive rejects to _archive/.

    Idempotent — skips files that already have a 'filtered' key in frontmatter.
    Returns {'passed': int, 'rejected': int}.
    """
    filters = load_filters()
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    passed_count = 0
    rejected_count = 0

    for file_path in sorted(IDEAS_DIR.glob("*.md")):
        post = load_idea(file_path)

        # Idempotency: skip already-filtered files
        if "filtered" in post.metadata:
            if post.get("filtered") == "passed":
                passed_count += 1
            else:
                rejected_count += 1
            continue

        reason = check_filters(post, filters)

        if reason is not None:
            post["filtered"] = "rejected"
            post["filter_reason"] = reason
            save_idea(post, file_path)
            shutil.move(str(file_path), str(ARCHIVE_DIR / file_path.name))
            rejected_count += 1
        else:
            post["filtered"] = "passed"
            save_idea(post, file_path)
            passed_count += 1

    print(
        f"Pre-filter complete: {passed_count} passed, "
        f"{rejected_count} rejected (archived)"
    )
    return {"passed": passed_count, "rejected": rejected_count}


if __name__ == "__main__":
    run_prefilter()

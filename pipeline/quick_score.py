import asyncio
import os
from pathlib import Path

import frontmatter

from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, save_idea

IDEAS_DIR = Path("1_ideas")
SHORTLIST_THRESHOLD_INVEST = 6
SHORTLIST_THRESHOLD_BUILD = 6

REQUIRED_KEYS = {"invest_score", "build_score", "category", "one_liner", "invest_rationale", "build_rationale"}


async def score_one_idea(post: frontmatter.Post, prompt_template: str) -> dict | None:
    name = post.get("name", "Unknown")
    url = post.get("url", "")
    round_raw = post.get("round_raw", "Unknown")
    description = post.content

    prompt = prompt_template.format(
        name=name,
        url=url,
        round_raw=round_raw,
        description=description,
    )

    result = await call_llm(prompt, model=os.getenv("OPENROUTER_MODEL_LIGHT"), json_mode=True)

    if isinstance(result, Exception) or result is None:
        return None

    if not isinstance(result, dict):
        return None

    if not REQUIRED_KEYS.issubset(result.keys()):
        return None

    invest_score = max(1, min(10, int(result.get("invest_score", 0))))
    build_score = max(1, min(10, int(result.get("build_score", 0))))

    return {
        "invest_score": invest_score,
        "build_score": build_score,
        "category": result.get("category"),
        "one_liner": result.get("one_liner"),
        "invest_rationale": result.get("invest_rationale"),
        "build_rationale": result.get("build_rationale"),
    }


async def run_quick_score() -> dict:
    prompt_template = load_prompt("quick_score")

    all_md_files = sorted(IDEAS_DIR.glob("*.md"))

    to_score = []
    skipped = 0

    for file_path in all_md_files:
        post = load_idea(file_path)
        if post.get("filtered") != "passed":
            continue
        if "invest_score" in post.metadata:
            skipped += 1
            continue
        to_score.append((file_path, post))

    print(f"Quick scoring {len(to_score)} ideas (skipping {skipped} already scored)...")

    tasks = [score_one_idea(post, prompt_template) for _, post in to_score]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scored_count = 0
    failed_count = 0

    for (file_path, post), result in zip(to_score, results):
        if isinstance(result, Exception) or result is None:
            print(f"  ERROR scoring {file_path.name}: {result}")
            failed_count += 1
            continue

        post["invest_score"] = result["invest_score"]
        post["build_score"] = result["build_score"]
        post["category"] = result["category"]
        post["one_liner"] = result["one_liner"]
        post["invest_rationale"] = result["invest_rationale"]
        post["build_rationale"] = result["build_rationale"]

        save_idea(post, file_path)
        scored_count += 1

    # Build shortlist by re-scanning all passed ideas
    shortlist = []
    for file_path in sorted(IDEAS_DIR.glob("*.md")):
        post = load_idea(file_path)
        if post.get("filtered") != "passed":
            continue
        invest = post.get("invest_score", 0) or 0
        build = post.get("build_score", 0) or 0
        if invest >= SHORTLIST_THRESHOLD_INVEST or build >= SHORTLIST_THRESHOLD_BUILD:
            shortlist.append(str(file_path))

    print(f"Scored: {scored_count}, Failed: {failed_count}, Shortlisted: {len(shortlist)}")

    return {
        "scored": scored_count,
        "failed": failed_count,
        "shortlist": shortlist,
        "shortlist_count": len(shortlist),
    }


if __name__ == "__main__":
    asyncio.run(run_quick_score())

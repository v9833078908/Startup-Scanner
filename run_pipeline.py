import asyncio
import argparse
import logging
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from lib.logger import setup_logging
from lib.llm import get_llm_stats
from scouts.dealpad_parser import parse_dealpad
from pipeline.prefilter import run_prefilter
from pipeline.quick_score import run_quick_score
from pipeline.deep_research import run_deep_research
from pipeline.deep_analysis import run_deep_analysis
from pipeline.digest_generator import run_digest

log = logging.getLogger("pipeline")

IDEAS_DIR = Path("1_ideas")
ARCHIVE_DIR = Path("_archive")
RESEARCH_DIR = Path("2_research")
ANALYSIS_DIR = Path("3_analysis")
DIGESTS_DIR = Path("digests")

# All scoring/classification fields written by prefilter and quick_score
STRIP_FIELDS = [
    "filtered", "filter_reason",
    "invest_eligible", "build_eligible",
    "is_tech", "sector", "sector_match", "product_type", "b2b_b2c",
    "classification_status", "review_needed",
    "invest_score", "build_score",
    "has_product_signal", "founder_signal",
    "cis_transferable", "uniqueness", "market_potential", "round_fit",
    "category", "one_liner", "invest_rationale", "build_rationale",
]


def do_reset() -> None:
    """
    Reset full pipeline state for a clean re-run:
      a. Move all _archive/*.md back to 1_ideas/
      b. Delete all files/dirs in 2_research/
      c. Delete all .md files in 3_analysis/
      d. Delete all .md files in digests/
      e. Strip all scoring/classification fields from 1_ideas/*.md frontmatter
    """
    import frontmatter as fm
    from lib.utils import load_idea, save_idea

    IDEAS_DIR.mkdir(parents=True, exist_ok=True)

    # a. Restore archived ideas
    restored = 0
    if ARCHIVE_DIR.exists():
        for archived_file in sorted(ARCHIVE_DIR.glob("*.md")):
            dest = IDEAS_DIR / archived_file.name
            shutil.move(str(archived_file), str(dest))
            restored += 1

    # b. Clear 2_research/ (subdirs per startup)
    if RESEARCH_DIR.exists():
        for item in RESEARCH_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(str(item))
            else:
                item.unlink()

    # c. Clear 3_analysis/ .md files
    if ANALYSIS_DIR.exists():
        for f in ANALYSIS_DIR.glob("*.md"):
            f.unlink()

    # d. Clear digests/ .md files
    if DIGESTS_DIR.exists():
        for f in DIGESTS_DIR.glob("*.md"):
            f.unlink()

    # e. Strip scoring/classification fields from all idea files
    cleaned = 0
    for idea_file in sorted(IDEAS_DIR.glob("*.md")):
        try:
            post = load_idea(idea_file)
            changed = False
            for field in STRIP_FIELDS:
                if field in post.metadata:
                    del post.metadata[field]
                    changed = True
            if changed:
                save_idea(post, idea_file)
                cleaned += 1
        except Exception as exc:
            log.warning("Could not clean %s: %s", idea_file.name, exc)

    print(
        f"Reset: {restored} ideas restored from archive, "
        f"{cleaned} ideas cleaned, downstream dirs cleared"
    )


async def main(html_path: str, reset: bool = False) -> None:
    setup_logging()

    if reset:
        log.info("=== Resetting pipeline state ===")
        do_reset()

    log.info("=== Startup Scouting Pipeline ===")
    log.info("Input: %s", html_path)
    total_start = time.monotonic()

    # Step 1: Parse DealPad
    log.info("[1/6] Parsing DealPad HTML export...")
    parsed_count = parse_dealpad(html_path)

    # Step 2: Pre-filter (async — LLM classification)
    log.info("[2/6] Applying pre-filter (LLM classification)...")
    filter_result = await run_prefilter()

    # Step 3: Quick Score
    log.info("[3/6] Quick scoring via LLM...")
    score_result = await run_quick_score()

    # Step 4: Deep Research
    log.info("[4/6] Deep research on shortlisted startups...")
    research_result = await run_deep_research()

    # Step 5: Deep Analysis
    log.info("[5/6] Deep analysis via LLM...")
    analysis_result = await run_deep_analysis()

    # Step 6: Digest
    log.info("[6/6] Generating weekly digest...")
    digest_result = await run_digest()

    # Final summary
    total_time = time.monotonic() - total_start
    stats = get_llm_stats()

    log.info("=" * 50)
    log.info("Pipeline complete in %.1fs", total_time)
    log.info("  Parsed: %d ideas", parsed_count)
    log.info(
        "  Pre-filter: %s invest-eligible, %s build-eligible, %s hard-rejected",
        filter_result.get("invest_eligible", "?"),
        filter_result.get("build_eligible", "?"),
        filter_result.get("hard_rejected", "?"),
    )
    log.info(
        "  Scored: %s, Shortlisted: %s",
        score_result.get("scored", "?"), score_result.get("shortlist_count", "?"),
    )
    log.info("  Researched: %s", research_result.get("researched", "?"))
    log.info("  Analyzed: %s", analysis_result.get("analyzed", "?"))
    log.info("  Digest: %s", digest_result.get("digest_path", "?"))
    log.info("--- LLM Usage ---")
    log.info("  Calls: %d", stats["calls"])
    log.info("  Prompt tokens: %d", stats["prompt_tokens"])
    log.info("  Completion tokens: %d", stats["completion_tokens"])
    log.info("  LLM time: %.1fs", stats["total_time"])
    log.info("  Errors: %d", stats["errors"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the startup scouting pipeline end-to-end"
    )
    parser.add_argument(
        "--html",
        required=True,
        help="Path to DealPad HTML export file or directory",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Reset full pipeline state before running: restore archived ideas, "
            "clear 2_research/, 3_analysis/, digests/, strip all scoring fields"
        ),
    )
    args = parser.parse_args()

    if not Path(args.html).exists():
        print(f"Error: path not found: {args.html}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(args.html, reset=args.reset))

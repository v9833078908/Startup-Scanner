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
from pipeline.triage import run_triage
from pipeline.deep_research import run_deep_research
from pipeline.research_gate import run_research_gate
from pipeline.deep_analysis import run_deep_analysis
from pipeline.digest_generator import run_digest

log = logging.getLogger("pipeline")

IDEAS_DIR = Path("1_ideas")
ARCHIVE_DIR = Path("_archive")
RESEARCH_DIR = Path("2_research")
ANALYSIS_DIR = Path("3_analysis")
DIGESTS_DIR = Path("digests")

# All classification/triage/gate fields written by pipeline stages
STRIP_FIELDS = [
    # Pre-filter fields
    "filtered", "filter_reason",
    "invest_eligible", "build_eligible",
    "is_tech", "sector", "sector_match", "product_type", "b2b_b2c",
    "classification_status", "review_needed",
    # Triage fields
    "invest_priority", "build_candidate",
    "has_product_evidence", "has_founder_signal",
    "barriers", "one_liner", "category",
    # Research gate fields
    "analysis_ready", "build_priority",
    "has_team_data", "has_traction_data", "has_competitive_context",
    "ru_gap_detected", "oss_commercializable", "cross_sell_fit",
    "underserved_niche", "clear_localization_path",
]


def do_reset() -> None:
    """
    Reset full pipeline state for a clean re-run:
      a. Move all _archive/*.md back to 1_ideas/
      b. Delete all files/dirs in 2_research/ (including gate.md)
      c. Delete all .md files in 3_analysis/
      d. Delete all .md files in digests/
      e. Strip all classification/triage/gate fields from 1_ideas/*.md frontmatter
    """
    from lib.utils import load_idea, save_idea

    IDEAS_DIR.mkdir(parents=True, exist_ok=True)

    # a. Restore archived ideas
    restored = 0
    if ARCHIVE_DIR.exists():
        for archived_file in sorted(ARCHIVE_DIR.glob("*.md")):
            dest = IDEAS_DIR / archived_file.name
            shutil.move(str(archived_file), str(dest))
            restored += 1

    # b. Clear 2_research/ (subdirs per startup, includes gate.md)
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

    # e. Strip classification/triage/gate fields from all idea files
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

    log.info("=== Startup Scouting Pipeline (7-stage funnel) ===")
    log.info("Input: %s", html_path)
    total_start = time.monotonic()

    # [1/7] Parse DealPad
    log.info("[1/7] Parsing DealPad HTML export...")
    parsed_count = parse_dealpad(html_path)

    # [2/7] Pre-filter (LLM classification)
    log.info("[2/7] Applying pre-filter (LLM classification)...")
    filter_result = await run_prefilter()

    # [3/7] Triage (binary evidence signals)
    log.info("[3/7] Triage (binary evidence signals)...")
    triage_result = await run_triage()

    # [4/7] Deep research (scrape shortlisted)
    log.info("[4/7] Deep research on research candidates...")
    research_list = triage_result.get("research_list")
    research_result = await run_deep_research(shortlist=research_list)

    # [5/7] Research gate (analysis readiness check)
    log.info("[5/7] Research gate (analysis readiness check)...")
    gate_result = await run_research_gate()

    # [6/7] Deep analysis (heavy model, only analysis_ready)
    log.info("[6/7] Deep analysis via heavy model (analysis-ready only)...")
    analysis_ready_slugs = gate_result.get("analysis_ready_slugs", [])
    analysis_result = await run_deep_analysis(slugs=analysis_ready_slugs)

    # [7/7] Digest generation
    log.info("[7/7] Generating weekly digest...")
    digest_result = await run_digest()

    # Final summary
    total_time = time.monotonic() - total_start
    stats = get_llm_stats()

    log.info("=" * 50)
    log.info("Pipeline complete in %.1fs", total_time)
    log.info("  Parsed: %d ideas", parsed_count)
    log.info(
        "  Pre-filter: %s passed, %s hard-rejected",
        filter_result.get("passed", "?"),
        filter_result.get("hard_rejected", "?"),
    )
    log.info(
        "  Triage: %s triaged, research candidates: %s",
        triage_result.get("triaged", "?"),
        triage_result.get("research_count", "?"),
    )
    log.info("  Researched: %s", research_result.get("researched", "?"))
    log.info(
        "  Research gate: %s analysis-ready, %s filtered",
        gate_result.get("ready", "?"),
        gate_result.get("filtered", "?"),
    )
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
        description="Run the startup scouting pipeline end-to-end (7-stage funnel)"
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
            "clear 2_research/, 3_analysis/, digests/, strip all triage/gate fields"
        ),
    )
    args = parser.parse_args()

    if not Path(args.html).exists():
        print(f"Error: path not found: {args.html}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(args.html, reset=args.reset))

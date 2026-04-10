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
from lib.utils import load_idea, make_slug
from scouts.dealpad_parser import parse_dealpad
from pipeline.prefilter import run_prefilter
from pipeline.triage import run_triage
from pipeline.deep_research import run_deep_research  # legacy, kept for backward compat
from pipeline.research_gate import run_research_gate  # legacy, kept for backward compat
from pipeline.invest_research import run_invest_research
from pipeline.build_research import run_build_research
from pipeline.invest_gate import run_invest_gate
from pipeline.build_gate import run_build_gate
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
    # Triage build-track signals
    "replicability", "cis_gap_likelihood", "stack_fit", "route",
    # Research gate fields (legacy unified gate)
    "analysis_ready", "build_priority",
    "has_team_data", "has_traction_data", "has_competitive_context",
    "ru_gap_detected", "oss_commercializable", "cross_sell_fit",
    "underserved_niche", "clear_localization_path",
    # Dual-track gate fields
    "invest_analysis_ready", "build_analysis_ready",
    "cis_gap_confirmed", "replicable_confirmed", "oss_base_available",
    "market_demand_signals",
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


def _derive_route(post) -> str:
    """Derive route from idea frontmatter.

    If 'route' field exists (set by triage with build signals), use it directly.
    Otherwise fall back to invest_priority + build_candidate to compute route.
    """
    route = post.get("route")
    if route in ("invest", "build", "both", "skip"):
        return route
    # Fallback: derive from invest_priority + build_candidate
    ip = post.get("invest_priority", "low")
    bc = post.get("build_candidate", False)
    invest = ip in ("high", "medium")
    build = bc is True
    if invest and build:
        return "both"
    if invest:
        return "invest"
    if build:
        return "build"
    return "skip"


async def main(html_path: str, reset: bool = False) -> None:
    setup_logging()

    if reset:
        log.info("=== Resetting pipeline state ===")
        do_reset()

    log.info("=== Startup Scouting Pipeline (9-stage dual-track funnel) ===")
    log.info("Input: %s", html_path)
    total_start = time.monotonic()

    # [1/9] Parse DealPad
    log.info("[1/9] Parsing DealPad HTML export...")
    parsed_count = parse_dealpad(html_path)

    # [2/9] Pre-filter (LLM classification)
    log.info("[2/9] Applying pre-filter (LLM classification)...")
    filter_result = await run_prefilter()

    # [3/9] Triage (binary evidence signals + route)
    log.info("[3/9] Triage (binary evidence signals)...")
    triage_result = await run_triage()

    # Split research list by route
    research_list = triage_result.get("research_list", [])
    route_dist = triage_result.get("route_distribution", {})

    # Build route-specific slug lists by scanning idea files
    invest_slugs = []  # route == "invest" or "both"
    build_slugs = []   # route == "build" or "both"
    for idea_file in sorted(IDEAS_DIR.glob("*.md")):
        post = load_idea(idea_file)
        slug = make_slug(post.get("name", ""))
        if slug not in research_list:
            continue
        route = _derive_route(post)
        if route in ("invest", "both"):
            invest_slugs.append(slug)
        if route in ("build", "both"):
            build_slugs.append(slug)
        # Track route distribution if triage didn't provide it
        if not route_dist:
            route_dist[route] = route_dist.get(route, 0) + 1

    # [4/9] Invest research (Exa-powered, invest/both-routed only)
    log.info("[4/9] Invest research (Exa-powered, %d startups)...", len(invest_slugs))
    invest_research_result = await run_invest_research(invest_slugs)

    # [5/9] Build research (Exa-powered, build/both-routed only)
    log.info("[5/9] Build research (Exa-powered, %d startups)...", len(build_slugs))
    build_research_result = await run_build_research(build_slugs)

    # [6/9] Invest gate (analysis readiness for invest track)
    log.info("[6/9] Invest gate (%d startups)...", len(invest_slugs))
    invest_gate_result = await run_invest_gate(invest_slugs)

    # [7/9] Build gate (analysis readiness for build track)
    log.info("[7/9] Build gate (%d startups)...", len(build_slugs))
    build_gate_result = await run_build_gate(build_slugs)

    # [8/9] Deep analysis (merged analysis-ready from both gates)
    invest_ready = invest_gate_result.get("invest_analysis_ready_slugs", [])
    build_ready = build_gate_result.get("build_analysis_ready_slugs", [])
    all_analysis_ready = list(dict.fromkeys(invest_ready + build_ready))  # dedupe, preserve order
    log.info(
        "[8/9] Deep analysis (%d startups from %d invest + %d build)...",
        len(all_analysis_ready), len(invest_ready), len(build_ready),
    )
    analysis_result = await run_deep_analysis(slugs=all_analysis_ready)

    # [9/9] Digest generation
    log.info("[9/9] Generating weekly digest...")
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
    log.info(
        "  Route: invest=%s, build=%s, both=%s, skip=%s",
        route_dist.get("invest", "?"),
        route_dist.get("build", "?"),
        route_dist.get("both", "?"),
        route_dist.get("skip", "?"),
    )
    log.info("  Invest research: %s", invest_research_result.get("researched", "?"))
    log.info("  Build research: %s", build_research_result.get("researched", "?"))
    log.info("  Invest gate: %s ready", invest_gate_result.get("ready", "?"))
    log.info("  Build gate: %s ready", build_gate_result.get("ready", "?"))
    log.info("  Analysis: %s (merged)", analysis_result.get("analyzed", "?"))
    log.info("  Digest: %s", digest_result.get("digest_path", "?"))
    log.info("--- LLM Usage ---")
    log.info("  Calls: %d", stats["calls"])
    log.info("  Prompt tokens: %d", stats["prompt_tokens"])
    log.info("  Completion tokens: %d", stats["completion_tokens"])
    log.info("  LLM time: %.1fs", stats["total_time"])
    log.info("  Errors: %d", stats["errors"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the startup scouting pipeline end-to-end (9-stage dual-track funnel)"
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

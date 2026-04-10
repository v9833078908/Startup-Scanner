import asyncio
import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from scouts.dealpad_parser import parse_dealpad
from pipeline.prefilter import run_prefilter
from pipeline.quick_score import run_quick_score
from pipeline.deep_research import run_deep_research
from pipeline.deep_analysis import run_deep_analysis
from pipeline.digest_generator import run_digest


async def main(html_path: str) -> None:
    print("=== Startup Scouting Pipeline ===")
    print(f"Input: {html_path}")
    total_start = time.time()

    # Step 1: Parse DealPad
    print("\n[1/6] Parsing DealPad HTML export...")
    step_start = time.time()
    parsed_count = parse_dealpad(html_path)
    print(f"  Done in {time.time() - step_start:.1f}s")

    # Step 2: Pre-filter
    print("\n[2/6] Applying pre-filter...")
    step_start = time.time()
    filter_result = run_prefilter()
    print(f"  Done in {time.time() - step_start:.1f}s")

    # Step 3: Quick Score
    print("\n[3/6] Quick scoring via LLM...")
    step_start = time.time()
    score_result = await run_quick_score()
    print(f"  Done in {time.time() - step_start:.1f}s")

    # Step 4: Deep Research
    print("\n[4/6] Deep research on shortlisted startups...")
    step_start = time.time()
    research_result = await run_deep_research()
    print(f"  Done in {time.time() - step_start:.1f}s")

    # Step 5: Deep Analysis
    print("\n[5/6] Deep analysis via LLM...")
    step_start = time.time()
    analysis_result = await run_deep_analysis()
    print(f"  Done in {time.time() - step_start:.1f}s")

    # Step 6: Digest
    print("\n[6/6] Generating weekly digest...")
    step_start = time.time()
    digest_result = await run_digest()
    print(f"  Done in {time.time() - step_start:.1f}s")

    # Final summary
    total_time = time.time() - total_start
    print(f"\n{'=' * 50}")
    print(f"Pipeline complete in {total_time:.1f}s")
    print(f"  Parsed: {parsed_count} ideas")
    print(f"  Filtered: {filter_result.get('passed', '?')} passed, {filter_result.get('rejected', '?')} rejected")
    print(f"  Scored: {score_result.get('scored', '?')}, Shortlisted: {score_result.get('shortlist_count', '?')}")
    print(f"  Researched: {research_result.get('researched', '?')}")
    print(f"  Analyzed: {analysis_result.get('analyzed', '?')}")
    print(f"  Digest: {digest_result.get('digest_path', '?')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the startup scouting pipeline end-to-end"
    )
    parser.add_argument(
        "--html",
        required=True,
        help="Path to DealPad HTML export file or directory",
    )
    args = parser.parse_args()

    if not Path(args.html).exists():
        print(f"Error: path not found: {args.html}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main(args.html))

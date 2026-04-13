import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from lib.web_search import web_search
from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, make_slug

log = logging.getLogger("pipeline.build_research")

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")


def format_search_results(results: list[dict]) -> str:
    """Format search results into readable text for prompt injection."""
    if not results:
        return "(No web search results found)"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"### Result {i}: {r['title']}")
        lines.append(f"URL: {r['url']}")
        lines.append(r["text"][:1500])
        lines.append("")
    return "\n".join(lines)


def _section(title: str, value) -> str:
    """Format a research section as markdown."""
    if isinstance(value, list):
        items = "\n".join(f"- {item}" for item in value)
        return f"### {title}\n{items}\n"
    return f"### {title}\n{value}\n"


async def research_one_build(post, slug: str) -> dict:
    """Research one startup for build track using web search."""
    research_dir = RESEARCH_DIR / slug
    research_dir.mkdir(parents=True, exist_ok=True)

    name = post.get("name", slug)
    category = post.get("category", post.get("sector", "technology"))
    description = post.content or ""

    # Step 1: Web search for CIS competitors
    cis_queries = [
        f"{category} Россия",
        f"{category} аналог CIS",
    ]
    cis_results = []
    for q in cis_queries:
        results = await web_search(q, num_results=5)
        cis_results.extend(results)

    # Step 2: Web search for OSS alternatives
    oss_queries = [
        f"{name} open source alternative github",
    ]
    oss_results = []
    for q in oss_queries:
        results = await web_search(q, num_results=5)
        oss_results.extend(results)

    cis_text = format_search_results(cis_results)
    oss_text = format_search_results(oss_results)

    # Step 3: LLM synthesis
    prompt_template = load_prompt("build_research")
    prompt = (
        prompt_template
        .replace("{name}", str(name))
        .replace("{category}", str(category))
        .replace("{description}", str(description)[:2000])
        .replace("{cis_search_results}", cis_text)
        .replace("{oss_search_results}", oss_text)
    )

    result = await call_llm(
        prompt, model=os.getenv("OPENROUTER_MODEL_LIGHT"), json_mode=True
    )

    # Step 4: Write build_research.md
    if isinstance(result, dict):
        body = (
            _section("Category Overview", result.get("category_overview", "N/A"))
            + "\n"
            + _section("CIS Competitors", result.get("cis_competitors", "N/A"))
            + "\n"
            + _section("CIS Gap Analysis", result.get("cis_gap_analysis", "N/A"))
            + "\n"
            + _section("OSS Alternatives", result.get("oss_alternatives", "N/A"))
            + "\n"
            + _section("Replication Assessment", result.get("replication_assessment", "N/A"))
            + "\n"
            + _section("Market Size Signals", result.get("market_size_signals", "N/A"))
            + "\n"
            + _section("Risks", result.get("risks", "N/A"))
        )
    else:
        body = "(LLM synthesis failed — no structured data available)"

    build_research_path = research_dir / "build_research.md"
    build_research_path.write_text(
        f"# Build Research: {name}\n\n"
        f"> Based on web search ({len(cis_results)} CIS results, "
        f"{len(oss_results)} OSS results, "
        f"backends: {','.join(set(r.get('backend', '?') for r in cis_results + oss_results))}). "
        f"Generated {datetime.utcnow().isoformat()}\n\n"
        f"{body}",
        encoding="utf-8",
    )

    log.info(
        "Build research done for %s (%d CIS, %d OSS results)",
        slug, len(cis_results), len(oss_results),
    )
    return {
        "slug": slug,
        "cis_results": len(cis_results),
        "oss_results": len(oss_results),
        "status": "ok",
    }


async def run_build_research(slugs: list[str]) -> dict:
    """Run build research on all build-routed startups.

    Takes explicit slug list. Checks each idea's route to verify it applies.
    Skips if build_research.md already exists (idempotent).
    """
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    # Build slug-to-idea mapping
    idea_map = {}
    for idea_file in sorted(IDEAS_DIR.glob("*.md")):
        try:
            post = load_idea(idea_file)
            file_slug = make_slug(post.get("name", ""))
            idea_map[file_slug] = post
        except Exception:
            continue

    pending = []
    skipped = 0

    for slug in slugs:
        post = idea_map.get(slug)
        if post is None:
            log.warning("No idea file found for slug: %s", slug)
            continue

        # Only process build or both routes
        route = post.get("route", "")
        if route not in ("build", "both"):
            log.info("Skipping %s: route=%s (not build/both)", slug, route)
            skipped += 1
            continue

        # Idempotency: skip if already researched
        if (RESEARCH_DIR / slug / "build_research.md").exists():
            log.info("Skipping %s: build_research.md already exists", slug)
            skipped += 1
            continue

        pending.append((post, slug))

    log.info("Build research: %d to process, %d skipped", len(pending), skipped)

    # Limit concurrency to avoid DDG/Sonar rate limits
    sem = asyncio.Semaphore(5)

    async def _throttled(post, slug):
        async with sem:
            return await research_one_build(post, slug)

    tasks = [_throttled(p, s) for p, s in pending]

    t0 = time.monotonic()
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success = sum(1 for r in results if not isinstance(r, Exception))
    failed = sum(1 for r in results if isinstance(r, Exception))
    for r in results:
        if isinstance(r, Exception):
            log.error("Build research failed: %s", r)

    elapsed = time.monotonic() - t0
    log.info(
        "Build research done in %.1fs: %d succeeded, %d failed, %d skipped",
        elapsed, success, failed, skipped,
    )

    return {"researched": success, "failed": failed, "skipped": skipped}


if __name__ == "__main__":
    asyncio.run(run_build_research([]))

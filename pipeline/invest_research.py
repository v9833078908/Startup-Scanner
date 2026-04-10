import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from lib.exa_client import exa_search
from lib.llm import call_llm, load_prompt
from lib.scraper import scrape_website
from lib.utils import load_idea, make_slug

log = logging.getLogger("pipeline.invest_research")

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")


def format_exa_results(results: list[dict]) -> str:
    """Format Exa search results into readable text for prompt injection."""
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


async def research_one_invest(post, slug: str) -> dict:
    """Research one startup for invest track using Exa search."""
    research_dir = RESEARCH_DIR / slug
    research_dir.mkdir(parents=True, exist_ok=True)

    name = post.get("name", slug)
    url = post.get("url", "")
    round_raw = post.get("round_raw", "Unknown")
    description = post.content or ""

    # Step 1: Scrape website (reuse existing scraper)
    website_text = await scrape_website(url) if url else ""
    website_path = research_dir / "website.md"
    if not website_path.exists():
        website_path.write_text(
            f"# Website Content: {name}\n\n"
            f"**URL:** {url}\n"
            f"**Scraped:** {datetime.utcnow().isoformat()}\n\n"
            f"{website_text if website_text else '(Website could not be reached)'}",
            encoding="utf-8",
        )

    # Step 2: Exa search for invest-relevant data (run sync SDK in thread)
    queries = [
        f'"{name}" founders team',
        f'"{name}" funding traction revenue',
    ]
    all_exa_results = []
    for q in queries:
        results = await asyncio.to_thread(exa_search, q, num_results=3)
        all_exa_results.extend(results)

    exa_text = format_exa_results(all_exa_results)

    # Step 3: LLM synthesis from Exa results + website
    prompt_template = load_prompt("invest_research")
    prompt = (
        prompt_template
        .replace("{name}", str(name))
        .replace("{url}", str(url))
        .replace("{round_raw}", str(round_raw))
        .replace("{description}", str(description)[:2000])
        .replace("{website_content}", website_text[:3000])
        .replace("{exa_results}", exa_text)
    )

    result = await call_llm(
        prompt, model=os.getenv("OPENROUTER_MODEL_LIGHT"), json_mode=True
    )

    # Step 4: Write invest_research.md
    if isinstance(result, dict):
        body = (
            _section("Summary", result.get("summary", "N/A"))
            + "\n"
            + _section("Founders", result.get("founders", "N/A"))
            + "\n"
            + _section("Business Model", result.get("business_model", "N/A"))
            + "\n"
            + _section("Traction", result.get("traction", "N/A"))
            + "\n"
            + _section("Competitors", result.get("competitors", "N/A"))
            + "\n"
            + _section("Funding History", result.get("funding_history", "N/A"))
            + "\n"
            + _section("Risks", result.get("risks", "N/A"))
        )
    else:
        body = str(result)

    invest_research_path = research_dir / "invest_research.md"
    invest_research_path.write_text(
        f"# Invest Research: {name}\n\n"
        f"> Based on Exa web search ({len(all_exa_results)} results) "
        f"and website scrape. Generated {datetime.utcnow().isoformat()}\n\n"
        f"{body}",
        encoding="utf-8",
    )

    log.info("Invest research done for %s (%d Exa results)", slug, len(all_exa_results))
    return {"slug": slug, "exa_results": len(all_exa_results), "status": "ok"}


async def run_invest_research(slugs: list[str]) -> dict:
    """Run invest research on all invest-routed startups.

    Takes explicit slug list. Checks each idea's route to verify it applies.
    Skips if invest_research.md already exists (idempotent).
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

    tasks = []
    skipped = 0

    for slug in slugs:
        post = idea_map.get(slug)
        if post is None:
            log.warning("No idea file found for slug: %s", slug)
            continue

        # Only process invest or both routes
        route = post.get("route", "")
        if route not in ("invest", "both"):
            log.info("Skipping %s: route=%s (not invest/both)", slug, route)
            skipped += 1
            continue

        # Idempotency: skip if already researched
        if (RESEARCH_DIR / slug / "invest_research.md").exists():
            log.info("Skipping %s: invest_research.md already exists", slug)
            skipped += 1
            continue

        tasks.append(research_one_invest(post, slug))

    log.info("Invest research: %d to process, %d skipped", len(tasks), skipped)

    t0 = time.monotonic()
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success = sum(1 for r in results if not isinstance(r, Exception))
    failed = sum(1 for r in results if isinstance(r, Exception))
    for r in results:
        if isinstance(r, Exception):
            log.error("Invest research failed: %s", r)

    elapsed = time.monotonic() - t0
    log.info(
        "Invest research done in %.1fs: %d succeeded, %d failed, %d skipped",
        elapsed, success, failed, skipped,
    )

    return {"researched": success, "failed": failed, "skipped": skipped}


if __name__ == "__main__":
    asyncio.run(run_invest_research([]))

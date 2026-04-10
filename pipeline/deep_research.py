import asyncio
import os
from datetime import datetime
from pathlib import Path

import frontmatter

from lib.llm import call_llm
from lib.scraper import scrape_website
from lib.utils import make_slug, load_idea

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")


async def research_one(post: frontmatter.Post, slug: str) -> dict:
    research_dir = RESEARCH_DIR / slug
    research_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Scrape website
    url = post.get("url", "")
    website_text = await scrape_website(url) if url else ""

    name = post.get("name", slug)
    website_path = research_dir / "website.md"
    website_path.write_text(
        f"# Website Content: {name}\n\n"
        f"**URL:** {url}\n"
        f"**Scraped:** {datetime.utcnow().isoformat()}\n\n"
        f"{website_text if website_text else '(Website could not be reached)'}",
        encoding="utf-8",
    )

    # Step 2: LLM research synthesis (using model's training data -- NOT real web search)
    prompt = (
        f"You are a startup analyst. Based on the following information about a startup, "
        f"provide a research summary.\n\n"
        f"Name: {name}\n"
        f"URL: {url}\n"
        f"Round: {post.get('round_raw', 'Unknown')}\n"
        f"Description: {post.content}\n"
        f"Website content: {website_text[:2000]}\n\n"
        f"Provide a research summary covering: what the company does, founders (if known), "
        f"business model, competitive landscape, traction signals, and potential risks.\n"
        f"Return as JSON with keys: summary, founders, business_model, competitors, traction, risks"
    )

    result = await call_llm(prompt, model=os.getenv("OPENROUTER_MODEL_LIGHT"), json_mode=True)

    # Format result into readable sections
    def _section(title: str, value) -> str:
        if isinstance(value, list):
            items = "\n".join(f"- {item}" for item in value)
            return f"### {title}\n{items}\n"
        return f"### {title}\n{value}\n"

    if isinstance(result, dict):
        body = (
            _section("Summary", result.get("summary", "N/A"))
            + "\n"
            + _section("Founders", result.get("founders", "N/A"))
            + "\n"
            + _section("Business Model", result.get("business_model", "N/A"))
            + "\n"
            + _section("Competitors", result.get("competitors", "N/A"))
            + "\n"
            + _section("Traction", result.get("traction", "N/A"))
            + "\n"
            + _section("Risks", result.get("risks", "N/A"))
        )
    else:
        body = str(result)

    research_path = research_dir / "web_research.md"
    research_path.write_text(
        f"# Research Summary: {name}\n\n"
        f"> Note: This research is synthesized from the startup's website and LLM training data. "
        f"It is NOT based on real-time web search.\n\n"
        f"{body}",
        encoding="utf-8",
    )

    return {
        "slug": slug,
        "website_scraped": bool(website_text),
        "research_dir": str(research_dir),
    }


async def run_deep_research(shortlist: list[str] | None = None) -> dict:
    # Output goes to 2_research/{slug}/ directories
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    if shortlist is None:
        # Scan IDEAS_DIR for shortlisted startups (invest_score >= 6 OR build_score >= 6)
        candidates = []
        for idea_file in sorted(IDEAS_DIR.glob("*.md")):
            try:
                post = load_idea(idea_file)
                invest_score = post.get("invest_score", 0) or 0
                build_score = post.get("build_score", 0) or 0
                if invest_score >= 6 or build_score >= 6:
                    slug = make_slug(post.get("name", idea_file.stem))
                    candidates.append((post, slug))
            except Exception:
                continue
    else:
        # Explicit slug list provided — find matching idea files
        candidates = []
        for slug in shortlist:
            for idea_file in sorted(IDEAS_DIR.glob("*.md")):
                try:
                    post = load_idea(idea_file)
                    if make_slug(post.get("name", "")) == slug:
                        candidates.append((post, slug))
                        break
                except Exception:
                    continue

    research_tasks = []
    skipped = 0
    slugs = []

    for post, slug in candidates:
        # Idempotency: skip if already researched
        if (RESEARCH_DIR / slug / "web_research.md").exists():
            skipped += 1
            slugs.append(slug)
            continue
        research_tasks.append(research_one(post, slug))
        slugs.append(slug)

    print(
        f"Researching {len(research_tasks)} startups "
        f"(skipping {skipped} already researched)..."
    )

    results = await asyncio.gather(*research_tasks, return_exceptions=True)

    success_count = sum(1 for r in results if not isinstance(r, Exception))
    fail_count = sum(1 for r in results if isinstance(r, Exception))

    for r in results:
        if isinstance(r, Exception):
            print(f"  ERROR: {r}")

    print(f"Research complete: {success_count} succeeded, {fail_count} failed")

    return {"researched": success_count, "failed": fail_count, "slugs": slugs}


if __name__ == "__main__":
    asyncio.run(run_deep_research())

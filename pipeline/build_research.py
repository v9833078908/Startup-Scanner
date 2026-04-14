import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from lib.web_search import web_search
from lib.llm import call_llm, load_prompt
from lib.utils import load_idea, make_slug

log = logging.getLogger("pipeline.build_research")

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")

# name, query template (uses {name}/{category}), DDG timelimit (None = no filter)
BUCKETS = [
    ("CIS_PLAYERS",   "{category} site:habr.com OR site:vc.ru",                                "y"),
    ("DEMAND_SIGNAL", '"купить {category}" OR "{category} цена" OR "{category} стоимость"',    None),
    ("GLOBAL_ALT",    '"{name} alternatives" OR "{name} vs"',                                  None),
    ("OSS_BASE",      "{name} open source self-hosted github",                                 None),
    ("COMMUNITY",     "{category} site:reddit.com",                                            "y"),
]

BUCKET_EMPTY_NOTES = {
    "CIS_PLAYERS":   "no CIS presence found on habr.com or vc.ru",
    "DEMAND_SIGNAL": "no RU commercial supply (landing pages) surfaced in search",
    "GLOBAL_ALT":    "no comparison/alternatives pages surfaced for this name",
    "OSS_BASE":      "no actionable OSS project surfaced in search",
    "COMMUNITY":     "no active reddit discussion surfaced for this category",
}

CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def _is_ru_landing(result: dict) -> bool:
    """A DEMAND_SIGNAL result counts as a RU landing if the domain is .ru
    OR the title/snippet contains Cyrillic text.
    """
    url = result.get("url", "") or ""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        host = ""
    if host.endswith(".ru") or ".ru/" in url.lower():
        return True
    blob = (result.get("title", "") or "") + " " + (result.get("text", "") or "")
    return bool(CYRILLIC_RE.search(blob))


def _format_bucketed(bucketed: dict[str, list[dict]]) -> str:
    """Flatten bucketed results into a single labeled string for prompt injection."""
    lines: list[str] = []
    for bucket_name, _, _ in BUCKETS:
        results = bucketed.get(bucket_name, [])
        if not results:
            lines.append(f"[{bucket_name}] (0 results — {BUCKET_EMPTY_NOTES[bucket_name]})")
            lines.append("")
            continue
        for i, r in enumerate(results, 1):
            title = (r.get("title") or "").strip()
            url = (r.get("url") or "").strip()
            snippet = (r.get("text") or "").strip().replace("\n", " ")[:800]
            lines.append(f"[{bucket_name}] result {i}: {title}")
            if url:
                lines.append(f"  URL: {url}")
            if snippet:
                lines.append(f"  {snippet}")
            lines.append("")
    return "\n".join(lines)


def _section(title: str, value) -> str:
    """Format a research section as markdown."""
    if isinstance(value, list):
        items = "\n".join(f"- {item}" for item in value)
        return f"### {title}\n{items}\n"
    return f"### {title}\n{value}\n"


async def _run_bucket(name: str, query: str, timelimit: str | None) -> tuple[str, list[dict]]:
    results = await web_search(query, num_results=5, timelimit=timelimit)
    return name, results[:5]


async def research_one_build(post, slug: str) -> dict:
    """Research one startup for build track using bucketed web search."""
    research_dir = RESEARCH_DIR / slug
    research_dir.mkdir(parents=True, exist_ok=True)

    name = post.get("name", slug)
    category = post.get("category", post.get("sector", "technology"))
    description = post.content or ""

    # Step 1: Run all buckets (semaphore in run_build_research bounds parallelism across startups;
    # within one startup, buckets fire in parallel — 5 concurrent DDG calls is fine).
    tasks = [
        _run_bucket(
            bname,
            tmpl.format(name=name, category=category),
            tlimit,
        )
        for bname, tmpl, tlimit in BUCKETS
    ]
    bucketed: dict[str, list[dict]] = {}
    for coro in asyncio.as_completed(tasks):
        bname, results = await coro
        bucketed[bname] = results

    # Step 2: Compute mechanical signals for sidecar
    demand_results = bucketed.get("DEMAND_SIGNAL", [])
    ru_landing_count = sum(1 for r in demand_results if _is_ru_landing(r))

    sidecar = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "name": name,
        "category": category,
        "buckets": {},
    }
    for bname, tmpl, tlimit in BUCKETS:
        results = bucketed.get(bname, [])
        entry = {
            "query": tmpl.format(name=name, category=category),
            "timelimit": tlimit,
            "count": len(results),
            "results": results,
        }
        if bname == "DEMAND_SIGNAL":
            entry["ru_landing_count"] = ru_landing_count
        sidecar["buckets"][bname] = entry

    (research_dir / "build_research_raw.json").write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Step 3: LLM synthesis
    bucketed_text = _format_bucketed(bucketed)
    prompt_template = load_prompt("build_research")
    prompt = (
        prompt_template
        .replace("{name}", str(name))
        .replace("{category}", str(category))
        .replace("{description}", str(description)[:2000])
        .replace("{bucketed_results}", bucketed_text)
    )

    result = await call_llm(
        prompt, model=os.getenv("OPENROUTER_MODEL_LIGHT"), json_mode=True
    )

    # Step 4: Write build_research.md
    if isinstance(result, dict):
        body = (
            _section("CIS Players", result.get("cis_players", "N/A"))
            + "\n"
            + _section("Demand Signal", result.get("demand_signal", "N/A"))
            + "\n"
            + _section("Global Alternatives", result.get("global_alt", "N/A"))
            + "\n"
            + _section("OSS Base", result.get("oss_base", "N/A"))
            + "\n"
            + _section("Community", result.get("community", "N/A"))
            + "\n"
            + _section("Replication Assessment", result.get("replication_assessment", "N/A"))
            + "\n"
            + _section("Risks", result.get("risks", "N/A"))
        )
    else:
        body = "(LLM synthesis failed — no structured data available)"

    total_results = sum(len(v) for v in bucketed.values())
    backends = sorted({r.get("backend", "?") for v in bucketed.values() for r in v})

    header = (
        f"# Build Research: {name}\n\n"
        f"> Bucketed web search: "
        + ", ".join(f"{bname}={len(bucketed.get(bname, []))}" for bname, _, _ in BUCKETS)
        + f" (total {total_results}, backends: {','.join(backends) or 'none'}). "
        f"demand_signal_ru_landings={ru_landing_count}. "
        f"Generated {datetime.utcnow().isoformat()}Z\n\n"
    )

    build_research_path = research_dir / "build_research.md"
    build_research_path.write_text(header + body, encoding="utf-8")

    log.info(
        "Build research done for %s (%s, ru_landings=%d)",
        slug,
        ", ".join(f"{bname}={len(bucketed.get(bname, []))}" for bname, _, _ in BUCKETS),
        ru_landing_count,
    )
    return {
        "slug": slug,
        "total_results": total_results,
        "ru_landing_count": ru_landing_count,
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

    # Limit concurrency across startups — each one fires 5 bucket queries in parallel.
    sem = asyncio.Semaphore(2)

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

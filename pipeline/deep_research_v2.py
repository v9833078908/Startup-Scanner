"""Stage 7.5 — Deep Research via Parallel AI.

For every startup that passed the build gate (~11-20 of ~400) run an
autonomous deep research task via Parallel AI (lib/parallel_client.py) and
write a rich research report to `2_research/{slug}/deep_research.md`.

Output feeds Stage 8 (Deep Analysis) so it can compute kill signals and
produce executive summaries on real facts instead of scarce DDG snippets.

Canonical module name
---------------------
`pipeline/deep_research_v2.py` is the OFFICIAL permanent name for Phase 2.
The `_v2` suffix is not "temporary deviation"; legacy `pipeline/deep_research.py`
from Phase 01-04 keeps its name for backward compatibility. A rename happens
only during Phase 4 cleanup (per 02-CONTEXT.md).

Accepted limitation — failed-task retry
--------------------------------------
When Parallel AI fails (API error, timeout, empty content) `run_deep_research_task`
returns a stub `{"content": "(Deep research failed: ...)", "citations": []}` and
`deep_research.md` is written with this stub. Re-runs skip stubs because of the
idempotency check on file existence. To retry a failed slug: manually delete
the stub file before re-running. Auto-retry of stubs is deferred to Phase 4
(see .env.example near `PARALLEL_API_KEY` for user-facing guidance).
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

import frontmatter

from lib.llm import load_prompt
from lib.parallel_client import run_deep_research_task
from lib.research_utils import _format_gate_signals, _format_raw_evidence
from lib.utils import load_idea, make_slug

log = logging.getLogger("pipeline.deep_research_v2")

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")


def _format_citations(citations: list[dict]) -> str:
    """Render citations list as markdown under `## Источники`.

    Empty citations → section is omitted (header-only markdown reads worse than
    absence).
    """
    if not citations:
        return ""
    lines = ["", "## Источники", ""]
    for c in citations:
        title = (c.get("title") or "").strip() or "(без заголовка)"
        url = (c.get("url") or "").strip()
        excerpt = (c.get("excerpt") or "").strip().replace("\n", " ")
        if url:
            lines.append(f"- [{title}]({url}) — {excerpt[:200]}")
        else:
            lines.append(f"- {title} — {excerpt[:200]}")
    lines.append("")
    return "\n".join(lines)


def _build_brief(post: frontmatter.Post, slug: str) -> str:
    """Build the research brief prompt for a startup.

    Uses .replace() (not .format()) — same pattern as all other pipeline
    modules, required because some prompts contain literal JSON braces that
    would break str.format (see Phase 01 decisions in STATE.md).
    """
    name = post.get("name", slug) or slug
    url = post.get("url", "") or ""
    description = (post.content or "")[:2000]
    round_raw = post.get("round_raw", "Unknown") or "Unknown"
    category = post.get("category", post.get("sector", "technology")) or "technology"

    # build_thesis was added to idea frontmatter by triage.py refactor (2026-04-14).
    # Missing/empty → fall back to explicit placeholder so the prompt still reads well.
    build_thesis = post.get("build_thesis") or "(none — triage did not produce a thesis)"

    # --- Preliminary context (added 02-04) ---------------------------------
    # All three reads are GRACEFUL — missing file → explicit placeholder.
    # Anti-anchoring framing lives in the prompt itself; this code only
    # routes the bytes into the template.
    research_dir = RESEARCH_DIR / slug

    website_path = research_dir / "website.md"
    website_summary = (
        website_path.read_text(encoding="utf-8")[:2000]
        if website_path.exists()
        else "(website.md not available)"
    )

    build_research_path = research_dir / "build_research.md"
    preliminary_findings = (
        build_research_path.read_text(encoding="utf-8")[:3000]
        if build_research_path.exists()
        else "(Stage 5 build research not available)"
    )

    gate_signals = _format_gate_signals(research_dir / "gate_build.md")

    raw_evidence = _format_raw_evidence(research_dir / "build_research_raw.json")

    template = load_prompt("deep_research_brief")
    return (
        template
        .replace("{name}", str(name))
        .replace("{url}", str(url))
        .replace("{description}", str(description))
        .replace("{round_raw}", str(round_raw))
        .replace("{category}", str(category))
        .replace("{build_thesis}", str(build_thesis))
        .replace("{website_summary}", website_summary)
        .replace("{preliminary_findings}", preliminary_findings)
        .replace("{gate_signals}", gate_signals)
        .replace("{raw_evidence}", raw_evidence)
    )


async def research_one_deep(post: frontmatter.Post, slug: str) -> dict:
    """Run deep research for a single startup and write deep_research.md.

    Returns {"slug": ..., "status": "ok"|"stub", "citations": N}.
    Never raises — errors are absorbed by run_deep_research_task and surfaced
    as a stub file so the pipeline can continue.
    """
    research_dir = RESEARCH_DIR / slug
    research_dir.mkdir(parents=True, exist_ok=True)

    name = post.get("name", slug) or slug
    brief = _build_brief(post, slug)

    result = await run_deep_research_task(brief)
    content = result.get("content", "") or ""
    citations = result.get("citations", []) or []

    is_stub = content.startswith("(Deep research failed:")

    header = (
        f"# Deep Research: {name}\n\n"
        f"> Generated {datetime.utcnow().isoformat()}Z — "
        f"Parallel AI Task API — {len(citations)} citations\n\n"
    )
    body = content.strip() + "\n" + _format_citations(citations)

    (research_dir / "deep_research.md").write_text(header + body, encoding="utf-8")

    if is_stub:
        log.warning("Deep research STUB written for %s (API failed)", slug)
        return {"slug": slug, "status": "stub", "citations": 0}

    log.info("Deep research OK for %s — %d citations", slug, len(citations))
    return {"slug": slug, "status": "ok", "citations": len(citations)}


async def run_deep_research_v2(slugs: list[str]) -> dict:
    """Stage 7.5 entry point — run deep research for a list of slugs.

    Explicit slug list comes from the build gate (same pattern as
    run_build_research). For each slug:
      - Load idea file; skip if missing.
      - Skip unless route is "build" or "both".
      - Skip if 2_research/{slug}/deep_research.md already exists (idempotent).
      - Otherwise run Parallel AI via research_one_deep.

    Concurrency bounded by Semaphore(3) — Parallel AI handles its own rate
    limits, so 3 concurrent requests is a conservative client-side cap.

    Returns {"researched": N_ok_or_stub, "failed": N_exceptions, "skipped": N}.
    """
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    # Map slug → idea post
    idea_map: dict[str, frontmatter.Post] = {}
    for idea_file in sorted(IDEAS_DIR.glob("*.md")):
        try:
            post = load_idea(idea_file)
            file_slug = make_slug(post.get("name", "") or "")
            if file_slug:
                idea_map[file_slug] = post
        except Exception:
            continue

    pending: list[tuple[frontmatter.Post, str]] = []
    skipped = 0

    for slug in slugs:
        post = idea_map.get(slug)
        if post is None:
            log.warning("No idea file found for slug: %s", slug)
            continue

        route = post.get("route", "") or ""
        if route not in ("build", "both"):
            log.info("Skipping %s: route=%s (not build/both)", slug, route)
            skipped += 1
            continue

        if (RESEARCH_DIR / slug / "deep_research.md").exists():
            log.info("Skipping %s: deep_research.md already exists", slug)
            skipped += 1
            continue

        pending.append((post, slug))

    log.info("Deep research v2: %d to process, %d skipped", len(pending), skipped)

    sem = asyncio.Semaphore(3)

    async def _throttled(post: frontmatter.Post, slug: str) -> dict:
        async with sem:
            return await research_one_deep(post, slug)

    tasks = [_throttled(p, s) for p, s in pending]

    t0 = time.monotonic()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - t0

    researched = sum(1 for r in results if not isinstance(r, Exception))
    failed = sum(1 for r in results if isinstance(r, Exception))
    for r in results:
        if isinstance(r, Exception):
            log.error("Deep research task raised: %s", r)

    log.info(
        "Deep research v2 done in %.1fs: %d researched, %d failed, %d skipped",
        elapsed, researched, failed, skipped,
    )

    return {"researched": researched, "failed": failed, "skipped": skipped}


if __name__ == "__main__":
    asyncio.run(run_deep_research_v2([]))

"""Unified web search interface.

Priority chain:
  - DDG (default) — free, no API key needed, returns raw snippets
  - Sonar (automatic fallback if DDG fails) — AI-synthesized, uses OPENROUTER_API_KEY
  - Exa (manual alternative via SEARCH_BACKEND=exa) — needs EXA_API_KEY, returns page text

Every result dict includes a 'backend' field so callers/prompts can distinguish
raw search results from AI-synthesized content.
"""

import asyncio
import logging
import os

log = logging.getLogger("web_search")


def _get_backend() -> str:
    """Return active search backend name."""
    backend = os.getenv("SEARCH_BACKEND", "").lower().strip()
    if backend == "exa":
        return "exa"
    return "ddg"


_DDG_SEM: asyncio.Semaphore | None = None


def _get_ddg_sem() -> asyncio.Semaphore:
    """Lazy-init module-level semaphore limiting concurrent DDG calls.

    DDG/Cloudflare blocks the IP when ~5+ requests fire simultaneously.
    Hung threads accumulate (asyncio.wait_for cancels the await but cannot
    kill the underlying socket-blocked thread), stalling the pipeline.

    Cap concurrency here so any caller of web_search() is rate-limited
    transparently, regardless of upstream concurrency structure.

    Tunable via DDG_MAX_CONCURRENT env var. Default 3.
    """
    global _DDG_SEM
    if _DDG_SEM is None:
        limit = int(os.getenv("DDG_MAX_CONCURRENT", "3"))
        _DDG_SEM = asyncio.Semaphore(limit)
    return _DDG_SEM


async def _ddg_search(
    query: str, num_results: int = 5, timelimit: str | None = None
) -> list[dict]:
    """Search via DuckDuckGo using ddgs library (v9.13+).

    DDGS.text() is synchronous — wrapped in asyncio.to_thread().
    Retries up to 3 times with exponential backoff on empty results / errors.
    Concurrent calls capped via module-level semaphore (see _get_ddg_sem).
    Returns list of {title, url, text, backend} dicts.
    Never raises — returns [] on failure.

    timelimit: None | 'd' | 'w' | 'm' | 'y' — DDG's native recency filter.
    DDG does not support ranges wider than 'y' (past year).
    """
    from ddgs import DDGS

    for attempt in range(3):
        try:
            def _sync_search():
                return DDGS().text(query, max_results=num_results, timelimit=timelimit)

            async with _get_ddg_sem():
                raw = await asyncio.wait_for(
                    asyncio.to_thread(_sync_search), timeout=30
                )

            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "text": r.get("body", "")[:2000],
                    "backend": "ddg",
                }
                for r in (raw or [])
            ]
            if results:
                return results
            # Empty results — might be rate-limited, retry
            if attempt < 2:
                await asyncio.sleep(2 ** attempt + 1)
        except asyncio.TimeoutError:
            log.warning("DDG search timeout (30s) attempt %d/3 for '%s'", attempt + 1, query)
            if attempt < 2:
                await asyncio.sleep(2 ** attempt + 1)
        except Exception as exc:
            log.warning("DDG search attempt %d/3 failed for '%s': %s", attempt + 1, query, exc)
            if attempt < 2:
                await asyncio.sleep(2 ** attempt + 1)
    return []


async def _sonar_search(
    query: str, num_results: int = 5, timelimit: str | None = None
) -> list[dict]:
    """Fallback search via Perplexity Sonar through OpenRouter.

    Uses call_llm() from lib/llm.py — gets shared semaphore, retry logic,
    and token telemetry. Returns a single result with synthesized answer.
    Cost: ~$0.005/request search fee + minor token costs.

    timelimit is not natively supported by Sonar — we prepend a recency hint.
    """
    try:
        from lib.llm import call_llm

        prompt_query = query
        if timelimit:
            recency = {"d": "past day", "w": "past week", "m": "past month", "y": "past year"}.get(
                timelimit, "past year"
            )
            prompt_query = f"Focus on results from the {recency} only. {query}"

        text = await call_llm(
            prompt=prompt_query,
            model="perplexity/sonar",
            json_mode=False,
            temperature=0.1,
        )
        text = str(text).strip()
        if not text:
            return []

        return [
            {
                "title": f"[Sonar] {query[:100]}",
                "url": "",
                "text": text[:2000],
                "backend": "sonar",
            }
        ]
    except Exception as exc:
        log.warning("Sonar fallback failed for '%s': %s", query, exc)
        return []


async def _exa_search_async(
    query: str, num_results: int = 5, timelimit: str | None = None
) -> list[dict]:
    """Search via Exa (delegates to lib.exa_client, run in thread)."""
    from datetime import datetime, timedelta, timezone

    from lib.exa_client import exa_search

    start_date = None
    if timelimit:
        days = {"d": 1, "w": 7, "m": 30, "y": 365}.get(timelimit, 365)
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    results = await asyncio.to_thread(exa_search, query, num_results, "auto", start_date)
    # Tag each result with backend
    for r in results:
        r["backend"] = "exa"
    return results


async def web_search(
    query: str, num_results: int = 5, timelimit: str | None = None
) -> list[dict]:
    """Search the web and return list of {title, url, text, backend} dicts.

    Backend selected by SEARCH_BACKEND env var:
      - "ddg" (default) — DuckDuckGo, free. Falls back to Sonar on failure.
        Concurrent DDG calls capped by DDG_MAX_CONCURRENT env var (default 3)
        to avoid Cloudflare rate-limit hangs.
      - "exa" — Exa API, requires EXA_API_KEY. No fallback.

    The 'backend' field in each result ('ddg', 'sonar', 'exa') lets callers
    distinguish raw search results from AI-synthesized content.

    timelimit: None | 'd' | 'w' | 'm' | 'y' — recency filter. DDG caps at 'y'
    (past year); Sonar gets a prepended hint; Exa gets start_published_date.

    Never raises — returns [] on failure.
    """
    backend = _get_backend()

    if backend == "exa":
        return await _exa_search_async(query, num_results, timelimit=timelimit)

    # DDG primary, Sonar fallback
    results = await _ddg_search(query, num_results, timelimit=timelimit)
    if not results:
        log.info("DDG returned no results for '%s', trying Sonar fallback", query)
        results = await _sonar_search(query, num_results, timelimit=timelimit)
    return results

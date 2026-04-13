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


async def _ddg_search(query: str, num_results: int = 5) -> list[dict]:
    """Search via DuckDuckGo using ddgs library (v9.13+).

    DDGS.text() is synchronous — wrapped in asyncio.to_thread().
    Retries up to 3 times with exponential backoff on empty results / errors.
    Returns list of {title, url, text, backend} dicts.
    Never raises — returns [] on failure.
    """
    from ddgs import DDGS

    for attempt in range(3):
        try:
            def _sync_search():
                return DDGS().text(query, max_results=num_results)

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


async def _sonar_search(query: str, num_results: int = 5) -> list[dict]:
    """Fallback search via Perplexity Sonar through OpenRouter.

    Uses call_llm() from lib/llm.py — gets shared semaphore, retry logic,
    and token telemetry. Returns a single result with synthesized answer.
    Cost: ~$0.005/request search fee + minor token costs.
    """
    try:
        from lib.llm import call_llm

        text = await call_llm(
            prompt=query,
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


async def _exa_search_async(query: str, num_results: int = 5) -> list[dict]:
    """Search via Exa (delegates to lib.exa_client, run in thread)."""
    from lib.exa_client import exa_search

    results = await asyncio.to_thread(exa_search, query, num_results)
    # Tag each result with backend
    for r in results:
        r["backend"] = "exa"
    return results


async def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web and return list of {title, url, text, backend} dicts.

    Backend selected by SEARCH_BACKEND env var:
      - "ddg" (default) — DuckDuckGo, free. Falls back to Sonar on failure.
      - "exa" — Exa API, requires EXA_API_KEY. No fallback.

    The 'backend' field in each result ('ddg', 'sonar', 'exa') lets callers
    distinguish raw search results from AI-synthesized content.

    Never raises — returns [] on failure.
    """
    backend = _get_backend()

    if backend == "exa":
        return await _exa_search_async(query, num_results)

    # DDG primary, Sonar fallback
    results = await _ddg_search(query, num_results)
    if not results:
        log.info("DDG returned no results for '%s', trying Sonar fallback", query)
        results = await _sonar_search(query, num_results)
    return results

import os
import logging

from exa_py import Exa

log = logging.getLogger("exa")


def get_exa_client() -> Exa:
    """Get Exa client. Raises if EXA_API_KEY not set."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        raise ValueError("EXA_API_KEY not set in .env")
    return Exa(api_key)


def exa_search(
    query: str,
    num_results: int = 5,
    search_type: str = "instant",
    start_date: str | None = None,
) -> list[dict]:
    """Search Exa and return list of {title, url, text} dicts.

    Uses synchronous Exa SDK (exa-py is sync).
    Returns empty list on failure -- never raises.

    search_type: "instant" (default, <150ms), "auto", "fast", "deep", "neural", "keyword".
    Instant is optimized neural with sub-150ms latency — fastest option that still
    returns full text content.

    start_date: optional ISO date (YYYY-MM-DD) passed as start_published_date
    to Exa's recency filter.
    """
    try:
        client = get_exa_client()
        kwargs = {
            "num_results": num_results,
            "type": search_type,
            "text": True,
        }
        if start_date:
            kwargs["start_published_date"] = start_date
        result = client.search_and_contents(query, **kwargs)
        return [
            {
                "title": r.title or "",
                "url": r.url or "",
                "text": (r.text or "")[:2000],
            }
            for r in result.results
        ]
    except Exception as exc:
        log.warning("Exa search failed for '%s': %s", query, exc)
        return []

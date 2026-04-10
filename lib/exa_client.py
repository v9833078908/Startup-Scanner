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
    query: str, num_results: int = 5, search_type: str = "auto"
) -> list[dict]:
    """Search Exa and return list of {title, url, text} dicts.

    Uses synchronous Exa SDK (exa-py is sync).
    Returns empty list on failure -- never raises.
    """
    try:
        client = get_exa_client()
        result = client.search_and_contents(
            query,
            num_results=num_results,
            type=search_type,
            text=True,
        )
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

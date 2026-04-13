import logging
import time

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


async def scrape_website(url: str, max_chars: int = 3000) -> str:
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        log.warning("GET %s failed: %s (%.1fs)", url, exc, time.monotonic() - t0)
        return ""
    except Exception as exc:
        log.warning("GET %s failed: %s (%.1fs)", url, exc, time.monotonic() - t0)
        return ""

    soup = BeautifulSoup(resp.text, "lxml")

    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    elapsed = time.monotonic() - t0
    log.info("GET %s → %d (%d chars, %.1fs)", url, resp.status_code, len(text), elapsed)
    return text[:max_chars]

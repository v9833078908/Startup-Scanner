import re
import unicodedata
from pathlib import Path

import dateparser
import frontmatter

MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}

CURRENCY_TO_USD = {
    "$": 1.0,
    "\u20ac": 1.08,   # €
    "\u00a3": 1.27,   # £
    "\u20bd": 0.011,  # ₽
}


def make_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^\w\s-]", "", normalized.lower())
    slug = re.sub(r"[-\s]+", "-", cleaned).strip("-")
    return slug[:50]


def parse_round_usd(raw: str) -> int | None:
    pattern = r"([$\u20ac\u00a3\u20bd])\s*([\d.]+)\s*([KMBkmb])?"
    match = re.search(pattern, raw)
    if not match:
        return None

    symbol, amount_str, suffix = match.groups()
    try:
        amount = float(amount_str)
    except ValueError:
        return None

    multiplier = MULTIPLIERS.get((suffix or "").upper(), 1)
    usd_rate = CURRENCY_TO_USD.get(symbol, 1.0)

    return int(amount * multiplier * usd_rate)


def parse_date(text: str) -> str | None:
    dt = dateparser.parse(text, languages=["ru", "en"])
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")


def load_idea(path: str | Path) -> frontmatter.Post:
    return frontmatter.load(str(path))


def save_idea(post: frontmatter.Post, path: str | Path) -> None:
    Path(path).write_text(frontmatter.dumps(post), encoding="utf-8")

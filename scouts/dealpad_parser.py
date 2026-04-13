import datetime
import logging
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
import frontmatter

from lib.utils import make_slug, parse_round_usd, parse_date

log = logging.getLogger("scouts.dealpad")

IDEAS_DIR = Path("1_ideas")

SPAM_KEYWORDS = ["обзоры", "fastfounder"]

# Regex to find a round amount line like "$115K", "$1.20M", "€2M", "Раунд: $500K, March 2026"
ROUND_PATTERN = re.compile(
    r"([$€£₽\u20ac\u00a3\u20bd]\s*[\d.,]+\s*[KMBkmb]?)",
    re.UNICODE,
)


def _parse_post_date(date_str: str) -> str:
    """Parse 'DD.MM.YYYY HH:MM:SS' from Telegram date title attribute → 'YYYY-MM-DD'."""
    if not date_str:
        return datetime.date.today().isoformat()
    # Take only the date part before the space
    date_part = date_str.split(" ")[0]  # "DD.MM.YYYY"
    try:
        parts = date_part.split(".")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return datetime.date.today().isoformat()


def _extract_round_info(full_text: str) -> tuple[str, int | None, str | None]:
    """
    Extract (round_raw, round_usd, round_date) from message text.

    DealPad format examples:
    - "Раунд: $115K, March 2026"
    - "$1.20M"
    - "raised $587.16K"
    Returns ("", None, None) if nothing found.
    """
    round_raw = ""
    round_usd = None
    round_date = None

    # Find the line containing a currency amount
    for line in full_text.split("\n"):
        match = ROUND_PATTERN.search(line)
        if match:
            round_raw = line.strip()
            round_usd = parse_round_usd(round_raw)
            # Try to parse a date from the same line
            # Remove the currency part to isolate potential date text
            date_candidate = ROUND_PATTERN.sub("", round_raw).strip(" ,:")
            if date_candidate:
                round_date = parse_date(date_candidate)
            break

    return round_raw, round_usd, round_date


def parse_html_file(html_path: str | Path) -> list[dict]:
    """
    Parse a single Telegram Desktop HTML export file.

    Returns a list of idea dicts with keys:
    name, url, round_raw, round_usd, round_date, description, message_id, post_date
    """
    html_path = Path(html_path)
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "lxml")

    # Select all message divs — both "message default clearfix" and
    # "message default clearfix joined" are included because BS4's .select()
    # on "div.message.default.clearfix" matches any div that has ALL three
    # classes as subsets of its class list (including joined messages).
    messages = soup.select("div.message.default.clearfix")

    ideas = []
    for div in messages:
        # a. Extract message_id
        raw_id = div.get("id", "")
        message_id = raw_id.replace("message", "") if raw_id else ""

        # b. Extract post_date from the .date element's title attribute
        date_el = div.find("div", class_="date") or div.select_one(".date.details")
        date_title = date_el.get("title", "") if date_el else ""
        post_date = _parse_post_date(date_title)

        # c. Get text element
        text_el = div.find("div", class_="text")
        if text_el is None:
            continue

        # d. Get full text
        full_text = text_el.get_text(separator="\n", strip=True)
        if not full_text:
            continue

        # e. Spam check
        lower_text = full_text.lower()
        if any(kw in lower_text for kw in SPAM_KEYWORDS):
            continue

        # f. Extract links for name and url
        links = text_el.find_all("a")
        if links:
            name = links[0].get_text(strip=True)
            url = links[0].get("href", "")
        else:
            # Fallback: first non-empty line
            first_line = next((ln for ln in full_text.split("\n") if ln.strip()), "")
            name = first_line.strip()
            url = ""

        if not name:
            continue

        # g. Extract round info
        round_raw, round_usd, round_date = _extract_round_info(full_text)

        # h. Build description: everything that is not the startup name and not the round line
        desc_lines = []
        for line in full_text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            # Skip the name line (exact match) and the round line (contains currency symbol)
            if stripped == name:
                continue
            if round_raw and stripped == round_raw:
                continue
            if ROUND_PATTERN.search(stripped) and len(stripped) < 80:
                continue
            desc_lines.append(stripped)
        description = "\n".join(desc_lines).strip() or full_text

        ideas.append(
            {
                "name": name,
                "url": url,
                "round_raw": round_raw,
                "round_usd": round_usd,
                "round_date": round_date,
                "description": description,
                "message_id": message_id,
                "post_date": post_date,
            }
        )

    return ideas


def save_ideas(ideas: list[dict], output_dir: Path = IDEAS_DIR) -> int:
    """
    Save parsed idea dicts as YAML-frontmatter Markdown files in output_dir.

    Idempotent — skips files that already exist.
    Returns number of new files saved.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for idea in ideas:
        slug = make_slug(idea["name"])
        date_prefix = idea["post_date"] or datetime.date.today().isoformat()
        filename = f"{date_prefix}_{slug}.md"
        output_path = output_dir / filename

        # Idempotency check — skip if file already exists
        if output_path.exists():
            continue

        content = (
            f"# {idea['name']}\n\n"
            f"**URL:** {idea['url']}\n"
            f"**Round:** {idea['round_raw']}\n\n"
            f"{idea['description']}"
        )

        post = frontmatter.Post(
            content,
            name=idea["name"],
            url=idea["url"],
            round_usd=idea["round_usd"],
            round_raw=idea["round_raw"],
            round_date=idea["round_date"],
            source="dealpad",
            source_id=idea["message_id"],
            parsed_at=datetime.datetime.utcnow().isoformat(),
        )

        output_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        saved_count += 1

    return saved_count


def parse_dealpad(html_input: str | Path) -> int:
    """
    Main entry point. Parse DealPad HTML export and save ideas to 1_ideas/.

    Accepts either a single HTML file path or a directory containing messages*.html files.
    Supports multi-file Telegram exports (messages.html, messages2.html, ...).

    Returns total number of new idea files saved.
    """
    html_path = Path(html_input)

    # Determine the list of HTML files to parse
    if html_path.is_dir():
        html_files = sorted(html_path.glob("messages*.html"))
    else:
        # Single file given — also pick up sibling files (messages2.html, etc.)
        html_files = sorted(html_path.parent.glob("messages*.html"))
        if not html_files:
            html_files = [html_path]

    if not html_files:
        log.error("No HTML files found at %s", html_input)
        return 0

    all_ideas: list[dict] = []
    for html_file in html_files:
        all_ideas.extend(parse_html_file(html_file))

    saved = save_ideas(all_ideas)
    log.info(
        "Parsed %d messages from %d file(s), saved %d new ideas",
        len(all_ideas), len(html_files), saved,
    )
    return saved


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scouts.dealpad_parser <path_to_messages.html>")
        sys.exit(1)
    parse_dealpad(sys.argv[1])

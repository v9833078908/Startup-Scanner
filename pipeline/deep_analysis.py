import asyncio
import os
from datetime import datetime
from pathlib import Path

import frontmatter
import yaml

from lib.llm import call_llm, load_prompt
from lib.utils import make_slug, load_idea

IDEAS_DIR = Path("1_ideas")
RESEARCH_DIR = Path("2_research")
ANALYSIS_DIR = Path("3_analysis")
WEIGHTS_PATH = Path("config/scoring_weights.yaml")


def load_weights() -> dict:
    return yaml.safe_load(WEIGHTS_PATH.read_text(encoding="utf-8"))


def compute_weighted_score(scores: dict, weights: dict) -> float:
    total = 0.0
    for criterion, weight in weights.items():
        raw = scores.get(criterion, 0)
        # Each criterion value may be a dict {score: N, rationale: "..."} or a plain number
        if isinstance(raw, dict):
            score = float(raw.get("score", 0))
        else:
            score = float(raw)
        total += score * weight
    return round(total, 1)


def determine_verdict(score: float, thresholds: dict) -> str:
    # Sort thresholds descending by value; return first label where score >= threshold
    sorted_thresholds = sorted(thresholds.items(), key=lambda x: x[1], reverse=True)
    for label, threshold in sorted_thresholds:
        if score >= threshold:
            return label.upper()
    # Fallback to the lowest threshold label
    return sorted_thresholds[-1][0].upper()


async def analyze_one(
    post: frontmatter.Post,
    slug: str,
    research_dir: Path,
    prompt_template: str,
    weights: dict,
) -> dict:
    # Load research data
    website_path = research_dir / "website.md"
    research_path = research_dir / "web_research.md"
    website_content = website_path.read_text(encoding="utf-8") if website_path.exists() else ""
    research_notes = research_path.read_text(encoding="utf-8") if research_path.exists() else ""

    name = post.get("name", slug)
    url = post.get("url", "")
    round_raw = post.get("round_raw", "Unknown")
    description = post.content

    # Build prompt by substituting template variables
    prompt = (
        prompt_template
        .replace("{name}", name)
        .replace("{url}", url)
        .replace("{round_raw}", str(round_raw))
        .replace("{description}", description)
        .replace("{website_content}", website_content[:3000])
        .replace("{research_notes}", research_notes[:3000])
    )

    result = await call_llm(
        prompt,
        model=os.getenv("OPENROUTER_MODEL_HEAVY"),
        json_mode=True,
        temperature=0.2,
    )

    if isinstance(result, Exception):
        raise result

    invest_scoring = result.get("invest_scoring", {})
    build_scoring = result.get("build_scoring", {})

    invest_total = compute_weighted_score(invest_scoring, weights["invest_mode"]["criteria"])
    build_total = compute_weighted_score(build_scoring, weights["build_mode"]["criteria"])

    invest_verdict = determine_verdict(invest_total, weights["invest_mode"]["thresholds"])
    build_verdict = determine_verdict(build_total, weights["build_mode"]["thresholds"])

    analyzed_at = datetime.utcnow().isoformat()

    # Build analysis markdown content
    def _criterion_lines(scoring: dict, criteria_weights: dict) -> str:
        lines = []
        for criterion in criteria_weights:
            raw = scoring.get(criterion, {})
            if isinstance(raw, dict):
                score = raw.get("score", "?")
                rationale = raw.get("rationale", "")
            else:
                score = raw
                rationale = ""
            lines.append(f"- **{criterion}**: {score}/10 — {rationale}")
        return "\n".join(lines)

    def _bullet_list(items) -> str:
        if not items:
            return "- N/A"
        if isinstance(items, list):
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    invest_lines = _criterion_lines(invest_scoring, weights["invest_mode"]["criteria"])
    build_lines = _criterion_lines(build_scoring, weights["build_mode"]["criteria"])

    body = (
        f"# Analysis: {name}\n\n"
        f"## Invest Score: {invest_total}/10 — {invest_verdict}\n\n"
        f"{invest_lines}\n\n"
        f"## Build Score: {build_total}/10 — {build_verdict}\n\n"
        f"{build_lines}\n\n"
        f"## Red Flags\n\n"
        f"{_bullet_list(result.get('red_flags', []))}\n\n"
        f"## Green Flags\n\n"
        f"{_bullet_list(result.get('green_flags', []))}\n\n"
        f"## CIS Adaptation\n\n"
        f"{result.get('cis_adaptation', 'N/A')}\n\n"
        f"## Risks\n\n"
        f"{_bullet_list(result.get('risks', []))}\n\n"
        f"## Next Steps\n\n"
        f"{_bullet_list(result.get('next_steps', []))}\n"
    )

    # Write analysis file with YAML frontmatter
    analysis_post = frontmatter.Post(
        body,
        name=name,
        url=url,
        invest_total=invest_total,
        build_total=build_total,
        invest_verdict=invest_verdict,
        build_verdict=build_verdict,
        analyzed_at=analyzed_at,
    )

    analysis_path = ANALYSIS_DIR / f"{slug}_analysis.md"
    analysis_path.write_text(frontmatter.dumps(analysis_post), encoding="utf-8")

    return {
        "slug": slug,
        "invest_total": invest_total,
        "build_total": build_total,
        "invest_verdict": invest_verdict,
        "build_verdict": build_verdict,
    }


async def run_deep_analysis(slugs: list[str] | None = None) -> dict:
    prompt_template = load_prompt("deep_analysis")
    weights = load_weights()
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    if slugs is None:
        # Scan 3_analysis/ target: find all research dirs that have web_research.md
        slugs = [
            d.name
            for d in sorted(RESEARCH_DIR.iterdir())
            if d.is_dir() and (d / "web_research.md").exists()
        ]

    analysis_tasks = []
    skipped = 0

    for slug in slugs:
        # Idempotency: skip if already analyzed
        if (ANALYSIS_DIR / f"{slug}_analysis.md").exists():
            skipped += 1
            continue

        # Find matching idea file in IDEAS_DIR
        post = None
        for idea_file in sorted(IDEAS_DIR.glob("*.md")):
            try:
                candidate = load_idea(idea_file)
                if make_slug(candidate.get("name", "")) == slug:
                    post = candidate
                    break
            except Exception:
                continue

        if post is None:
            # Create minimal stub post so analysis can still proceed
            post = frontmatter.Post("", name=slug, url="")

        research_dir = RESEARCH_DIR / slug
        analysis_tasks.append(
            analyze_one(post, slug, research_dir, prompt_template, weights)
        )

    print(
        f"Analyzing {len(analysis_tasks)} startups "
        f"(skipping {skipped} already analyzed)..."
    )

    results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

    success_count = sum(1 for r in results if not isinstance(r, Exception))
    fail_count = sum(1 for r in results if isinstance(r, Exception))

    for r in results:
        if isinstance(r, Exception):
            print(f"  ERROR: {r}")

    print(f"Analysis complete: {success_count} analyzed, {fail_count} failed")

    return {"analyzed": success_count, "failed": fail_count}


if __name__ == "__main__":
    asyncio.run(run_deep_analysis())

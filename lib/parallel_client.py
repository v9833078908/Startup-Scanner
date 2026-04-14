"""Async client for the Parallel AI Task API.

Thin httpx wrapper around https://api.parallel.ai/v1 — follows the project's
pattern of minimal API wrappers (see lib/exa_client.py). Used by Stage 7.5
(pipeline/deep_research_v2.py) to run autonomous deep research on startups
that passed the build gate.

API shape:
  POST /tasks/runs      → create a task, returns run_id
  GET  /tasks/runs/{id}/result?timeout=N → poll/block until result ready

The response payload carries `output.content` (markdown research text) and
`output.basis` — a list of basis items where each item wraps its own
`citations` array. Two-level iteration is required to flatten citations
(see extract_citations); a flat-list assumption causes KeyError at runtime.

Auth: PARALLEL_API_KEY env var, header `x-api-key`. The key is never logged
and never written to output files (threat T-02-01).
"""

import logging
import os
from typing import Any

import httpx

log = logging.getLogger("parallel_client")

BASE_URL = "https://api.parallel.ai/v1"
PROCESSOR = "core"  # $0.025/run — quality tier per 02-CONTEXT.md
TIMEOUT = 600  # seconds — result polling blocks until task completes


def _headers() -> dict[str, str]:
    """Build request headers. PARALLEL_API_KEY is loaded lazily so tests /
    imports don't require the key to be present at module load time."""
    api_key = os.getenv("PARALLEL_API_KEY") or ""
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }


async def create_task_run(
    input_text: str,
    output_description: str = "Detailed startup research report in Russian with citations",
    processor: str = PROCESSOR,
) -> str:
    """Create a Parallel AI task run. Returns the run_id.

    Raises httpx.HTTPStatusError on 4xx/5xx — caller decides retry policy.
    """
    payload = {
        "processor": processor,
        "input": input_text,
        "task_spec": {
            "output_schema": {
                "type": "text",
                "description": output_description,
            }
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{BASE_URL}/tasks/runs",
            headers=_headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    run_id = data.get("run_id") or data.get("run", {}).get("run_id")
    if not run_id:
        raise ValueError(f"Parallel AI create_task_run: no run_id in response: {data}")
    return run_id


async def get_task_result(run_id: str, timeout: int = TIMEOUT) -> dict[str, Any]:
    """Poll Parallel AI for a task's result. Returns full response dict with
    `run` and `output` keys.

    The timeout query param tells the API how long to block server-side
    before returning (max 600s). httpx client timeout is set slightly
    higher so network slack doesn't clip the server-side wait.

    Raises httpx.HTTPStatusError on 4xx/5xx.
    """
    async with httpx.AsyncClient(timeout=timeout + 30) as client:
        response = await client.get(
            f"{BASE_URL}/tasks/runs/{run_id}/result",
            headers=_headers(),
            params={"timeout": timeout},
        )
        response.raise_for_status()
        return response.json()


def extract_citations(output: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten output.basis → list of {url, title, excerpt} citations.

    CRITICAL: `output.basis` is a list of BASIS ITEMS, each of which wraps a
    `citations` array. Two-level iteration is required; a naive flat-list
    walk causes KeyError at runtime (verified in 02-RESEARCH.md Pitfall 2).
    """
    citations: list[dict[str, str]] = []
    for basis_item in output.get("basis", []) or []:
        for citation in basis_item.get("citations", []) or []:
            excerpts = citation.get("excerpts") or []
            excerpt = excerpts[0][:200] if excerpts else ""
            citations.append(
                {
                    "url": citation.get("url", "") or "",
                    "title": citation.get("title", "") or "",
                    "excerpt": excerpt,
                }
            )
    return citations


async def run_deep_research_task(
    input_text: str,
    output_description: str = "Detailed startup research report in Russian with citations",
) -> dict[str, Any]:
    """Convenience: create task + fetch result + extract citations.

    Returns {"content": str, "citations": list[dict]}. Never raises — on
    any failure returns a fallback dict with a "(Deep research failed: ...)"
    stub content and empty citations. Callers (pipeline/deep_research_v2.py)
    rely on this to keep the pipeline moving even when the API is flaky.

    Error messages must never leak the API key. httpx.HTTPStatusError
    stringifies the request URL but not headers, which is safe.
    """
    _log_first_output = not getattr(run_deep_research_task, "_logged", False)
    try:
        run_id = await create_task_run(input_text, output_description=output_description)
        log.info("Parallel AI task created: run_id=%s", run_id)

        result = await get_task_result(run_id)
        output = result.get("output", {}) or {}

        # Log full output structure once to confirm schema (then suppress).
        if _log_first_output:
            log.debug("Parallel AI first output payload: %s", result)
            run_deep_research_task._logged = True  # type: ignore[attr-defined]

        content = output.get("content", "") or ""
        citations = extract_citations(output)

        if not content:
            log.warning("Parallel AI returned empty content for run_id=%s", run_id)
            return {
                "content": "(Deep research failed: empty content from API)",
                "citations": [],
            }

        return {"content": content, "citations": citations}

    except httpx.HTTPStatusError as exc:
        log.error(
            "Parallel AI HTTP error %s: %s",
            exc.response.status_code,
            exc.response.text[:300],
        )
        return {
            "content": f"(Deep research failed: HTTP {exc.response.status_code})",
            "citations": [],
        }
    except Exception as exc:
        log.error("Parallel AI request failed: %s", exc)
        return {
            "content": f"(Deep research failed: {exc})",
            "citations": [],
        }

import os
import json
import logging
import re
import asyncio
import time
from pathlib import Path

from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("llm")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY") or "not-set",
)

semaphore = asyncio.Semaphore(5)

# Cumulative stats for the current pipeline run
_stats = {
    "calls": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "errors": 0,
    "total_time": 0.0,
}


def get_llm_stats() -> dict:
    return dict(_stats)


def reset_llm_stats() -> None:
    for k in _stats:
        _stats[k] = 0 if isinstance(_stats[k], int) else 0.0


async def call_llm(
    prompt: str,
    model: str | None = None,
    json_mode: bool = True,
    temperature: float = 0.1,
) -> dict | str:
    if model is None:
        model = os.getenv("OPENROUTER_MODEL_LIGHT")

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    async with semaphore:
        t0 = time.monotonic()
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**kwargs)
                elapsed = time.monotonic() - t0
                raw = response.choices[0].message.content or ""

                # Track token usage
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0

                _stats["calls"] += 1
                _stats["prompt_tokens"] += prompt_tokens
                _stats["completion_tokens"] += completion_tokens
                _stats["total_time"] += elapsed

                log.info(
                    "model=%s tokens=%d/%d time=%.1fs",
                    model, prompt_tokens, completion_tokens, elapsed,
                )

                if not json_mode:
                    return raw

                # Strip markdown code fences
                cleaned = re.sub(
                    r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE
                )
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    if attempt < 2:
                        log.warning(
                            "JSON parse failed (attempt %d/3), retrying", attempt + 1
                        )
                        await asyncio.sleep(2**attempt)
                        continue
                    log.error("JSON parse failed after 3 attempts, returning None")
                    return None

            except Exception as exc:
                _stats["errors"] += 1
                if attempt < 2:
                    log.warning("retry %d/3: %s", attempt + 1, exc)
                    await asyncio.sleep(2**attempt)
                else:
                    log.error("failed after 3 attempts: %s", exc)
                    raise

    return {} if json_mode else ""


async def call_llm_batch(
    items: list,
    prompt_fn: callable,
    model: str | None = None,
    json_mode: bool = True,
) -> list[dict | Exception]:
    tasks = [call_llm(prompt_fn(item), model=model, json_mode=json_mode) for item in items]
    return await asyncio.gather(*tasks, return_exceptions=True)


def load_prompt(name: str) -> str:
    path = Path(__file__).parent.parent / "prompts" / f"{name}.md"
    return path.read_text(encoding="utf-8")

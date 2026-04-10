import os
import json
import re
import asyncio
from pathlib import Path

from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY") or "not-set",
)

semaphore = asyncio.Semaphore(5)


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
        for attempt in range(3):
            try:
                response = await client.chat.completions.create(**kwargs)
                raw = response.choices[0].message.content or ""

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
                        await asyncio.sleep(2**attempt)
                        continue
                    return cleaned

            except Exception:
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                else:
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

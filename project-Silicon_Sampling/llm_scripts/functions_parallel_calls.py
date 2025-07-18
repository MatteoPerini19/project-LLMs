"""
functions_parallel_calls.py
───────────────────────────
Utility helpers for running *many* asynchronous calls with LiteLLM and for
tidy‑up post‑processing (JSON extraction, basic stats).

Import in your runner script with:
```python
from functions_parallel_calls import asynch_completion, _extract_json_payload, _safe_stdev
```
"""

from __future__ import annotations

import asyncio
import json
import re
import statistics
from contextlib import nullcontext as _nullctx
from typing import Any

import litellm as llm
from tenacity import retry, stop_after_attempt, wait_exponential

# Silence LiteLLM's chatty banner
llm.set_verbose = False


# ──────────────────────────────────────────────────────────────
# JSON helpers
# ──────────────────────────────────────────────────────────────
def _extract_json_payload(text: str) -> Any:
    """
    Isolate and parse a JSON object embedded in *text*.

    The function:
    • Strips Markdown fences  ```json … ```  if present.  
    • Keeps content from the first “{” to the last “}”.  
    • Normalises curly quotes to straight quotes.  
    • Attempts ``json.loads``. On failure, returns the cleaned raw string.

    Returns
    -------
    dict | list | str
        Parsed Python object or original string if parsing fails.
    """
    text = text.strip()

    # Remove ```json fences
    if text.startswith("```"):
        m = re.match(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()

    # Trim to outermost braces
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    # Normalise curly quotes
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _safe_stdev(seq: list[float]) -> float:
    """Return ``statistics.stdev(seq)`` if ``len(seq) ≥ 2`` else ``float('nan')``."""
    return statistics.stdev(seq) if len(seq) >= 2 else float("nan")


# ──────────────────────────────────────────────────────────────
# Async LiteLLM parallel wrapper
# ──────────────────────────────────────────────────────────────
_CONCURRENCY_DEFAULT = 10  # upper bound for in‑flight requests


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def _one_call(
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int | None = None,
    _sem: asyncio.Semaphore | None = None,
):
    """
    One asynchronous call to ``llm.acompletion`` guarded by an optional semaphore
    and with automatic retry (exponential back‑off, 3 attempts).

    Returns
    -------
    litellm.ModelResponse
    """
    sem_ctx = _sem or _nullctx()  # no‑op context if semaphore is None
    async with sem_ctx:
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        return await llm.acompletion(**kwargs)


async def _batch_runner(
    num_calls: int,
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int | None,
    concurrency: int,
):
    """Launch *num_calls* tasks concurrently; return list of responses/exceptions."""
    sem = asyncio.Semaphore(concurrency)
    tasks = [
        asyncio.create_task(_one_call(messages, model, max_tokens, sem))
        for _ in range(num_calls)
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)


def asynch_completion(
    *,
    num_calls: int,
    messages: list[dict[str, str]],
    model: str = "openai/gpt-4o",
    max_tokens: int | None = None,
    concurrency: int | None = None,
):
    """
    Fire *num_calls* parallel completions and wait for all to finish.

    Parameters
    ----------
    num_calls : int
        How many calls to send.
    messages : list[dict]
        Chat messages in OpenAI format.
    model : str, default ``"openai/gpt-4o"``
        Provider/model identifier.
    max_tokens : int | None
        Cap on tokens returned per completion.
    concurrency : int | None
        Max in‑flight requests (default: 10).

    Returns
    -------
    list[litellm.ModelResponse | Exception]
        Responses or raised exceptions (if any).
    """
    conc = concurrency or _CONCURRENCY_DEFAULT
    return asyncio.run(_batch_runner(num_calls, messages, model, max_tokens, conc))


__all__ = [
    "_extract_json_payload",
    "_safe_stdev",
    "asynch_completion",
]
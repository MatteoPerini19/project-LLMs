"""
litellm_client.py
=================
Network layer for the Qualtrics translation pipeline.

This thin wrapper around LiteLLM offers:
• A single public function  :func:`call_llm`
• Automatic retry with exponential back‑off on 429 / 5xx
• JSON validation of the model’s response
• Structured logging of every request / response round‑trip

No other module should touch the network; everyone else funnels their
prompts through this file so that timeouts, cost control, and telemetry
are enforced uniformly.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict

import litellm
from litellm import exceptions as lite_exc

from config import LLM_TIMEOUT, LOG_DIR, TEMPERATURE, MAX_RETRIES
from utils import safe_mkdirs

# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #


def _timestamp() -> str:
    """Return an ISO‑8601 timestamp with millisecond precision (UTC)."""
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _sha8(text: str) -> str:
    """Short SHA‑256 hash (8 hex chars) — handy for log correlation."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _write_log(entry: Dict[str, Any]) -> None:
    """
    Append *entry* as one JSON line to the daily LiteLLM log file.
    """
    safe_mkdirs(LOG_DIR)
    log_file = LOG_DIR / f"litellm_calls_{_timestamp()[:10]}.jsonl"
    with log_file.open("a", encoding="utf-8") as fh:
        json.dump(entry, fh, ensure_ascii=False)
        fh.write("\n")


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def call_llm(
    prompt: str,
    *,
    model: str,
    language: str,
    timeout: int = LLM_TIMEOUT,
    max_retries: int = MAX_RETRIES,
    temperature: float = TEMPERATURE,
) -> Dict[str, str]:
    """
    Send ``prompt`` to LiteLLM and return the parsed JSON as ``dict``.

    Parameters
    ----------
    prompt : str
        Fully‑formed prompt string, ready for the model.
    model : str
        Model name understood by LiteLLM (e.g., ``"gpt-4o-mini"``).
    language : str
        ISO‑639‑1 target language code (logged for traceability).
    timeout : int, optional
        Per‑call timeout in seconds (default: ``config.LLM_TIMEOUT``).
    max_retries : int, optional
        Number of attempts before giving up (default: 4).

    Returns
    -------
    dict[str, str]
        Mapping ``cell_id -> translated text``.

    Raises
    ------
    RuntimeError
        If the model returns non‑JSON output or all retries fail.
    """
    attempt = 0
    delay = 2  # initial back‑off seconds
    start_time = time.time()

    while True:
        attempt += 1
        try:
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout,
                temperature=temperature,
            )
            raw_text = (
                response["choices"][0]["message"]["content"].strip()
                if isinstance(response, dict)
                else str(response).strip()
            )
            parsed = json.loads(raw_text)
            if not isinstance(parsed, dict):
                raise ValueError("Model output is not a JSON object.")
            # Success: log and return
            latency_ms = int((time.time() - start_time) * 1000)
            _write_log(
                {
                    "timestamp": _timestamp(),
                    "model": model,
                    "temperature": temperature,
                    "language": language,
                    "prompt_hash": _sha8(prompt),
                    "input_tokens": response.get("usage", {}).get("prompt_tokens"),
                    "output_tokens": response.get("usage", {}).get("completion_tokens"),
                    "latency_ms": latency_ms,
                    "status": "ok",
                    "attempt": attempt,
                }
            )
            return parsed

        except (lite_exc.RateLimitError, lite_exc.APIError) as err:
            if attempt >= max_retries:
                raise RuntimeError(f"LiteLLM failed after {attempt} attempts.") from err
            time.sleep(delay)
            delay *= 2  # exponential back‑off

        except (json.JSONDecodeError, ValueError) as err:
            # Model answered but not with valid JSON → no retry, escalate
            _write_log(
                {
                    "timestamp": _timestamp(),
                    "model": model,
                    "language": language,
                    "prompt_hash": _sha8(prompt),
                    "latency_ms": int((time.time() - start_time) * 1000),
                    "status": "invalid_json",
                    "attempt": attempt,
                    "error": str(err),
                    "raw_output_excerpt": (raw_text[:2000] + "…")
                    if isinstance(raw_text, str)
                    else "n/a",
                }
            )
            raise RuntimeError("Model returned invalid JSON.") from err

        except Exception as err:  # pragma: no cover
            # Unknown fatal — log and propagate
            _write_log(
                {
                    "timestamp": _timestamp(),
                    "model": model,
                    "language": language,
                    "prompt_hash": _sha8(prompt),
                    "latency_ms": int((time.time() - start_time) * 1000),
                    "status": "fatal_error",
                    "attempt": attempt,
                    "error": str(err),
                }
            )
            raise
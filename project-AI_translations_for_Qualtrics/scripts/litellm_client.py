"""
litellm_client.py
=================
Network layer for the Qualtrics translation pipeline.

Single public entry point:
    call_llm(prompt: str, *, model: str | None, language: str, ...)

Responsibilities
----------------
• Load & sanitize API keys *before* any SDK import.
• Route OpenAI project keys to the new /responses API (sk-proj-*).
• Enforce JSON-only output via response_format and robust post‑parsing.
• Retry on transient 429/5xx errors with exponential backoff.
• Log every call (prompt hash, latency, token usage) to JSONL.
• (Optional) print first prompt/response for debugging, controlled via config.
"""

# --------------------------------------------------------------------------- #
# 0. Pre-flight: environment                             (NO SDK IMPORTS YET) #
# --------------------------------------------------------------------------- #
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]  # …/project-LLMs
load_dotenv(ROOT_DIR / ".env", override=True)

# Strip trailing whitespace/newlines that can poison HTTP headers
for _k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
    if _k in os.environ and os.environ[_k]:
        os.environ[_k] = os.environ[_k].strip()

# Map project id env var to what OpenAI SDK expects
if "OPENAI_PROJECT_ID" in os.environ and not os.environ.get("OPENAI_PROJECT"):
    os.environ["OPENAI_PROJECT"] = os.environ["OPENAI_PROJECT_ID"].strip()

# Force LiteLLM to use the Responses API unless explicitly disabled
if os.environ.get("LITELLM_USE_RESPONSES_API") is None:
    os.environ["LITELLM_USE_RESPONSES_API"] = "true"

# --------------------------------------------------------------------------- #
# 1. Standard library imports
# --------------------------------------------------------------------------- #
import hashlib
import json
import time
import ast
from datetime import datetime, timezone
from typing import Any, Dict

# --------------------------------------------------------------------------- #
# 2. Third‑party imports (SDKs AFTER env is correct)
# --------------------------------------------------------------------------- #
import litellm
from litellm import exceptions as lite_exc

# --------------------------------------------------------------------------- #
# 3. Local imports
# --------------------------------------------------------------------------- #
from config import (
    LLM_TIMEOUT,
    LOG_DIR,
    TEMPERATURE,
    MAX_RETRIES,
    USE_RESPONSES_API,
)
try:
    from config import PRINT_FIRST_PROMPT, PRINT_FIRST_RESPONSE
except ImportError:  # backward compat
    PRINT_FIRST_PROMPT = False
    PRINT_FIRST_RESPONSE = False

from utils import safe_mkdirs, extract_json_payload, escape_unescaped_quotes

# --------------------------------------------------------------------------- #
# 4. Constants / globals
# --------------------------------------------------------------------------- #
DEFAULT_MODEL = "openai/gpt-4o"  # if orchestrator doesn't pass a model

_printed_prompt_once = False
_printed_response_once = False
_last_prompt_snapshot: str | None = None


# --------------------------------------------------------------------------- #
# 5. Helper functions
# --------------------------------------------------------------------------- #
def _timestamp() -> str:
    """Return UTC ISO‑8601 timestamp with ms precision."""
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sha8(text: str) -> str:
    """Short SHA‑256 hash (8 hex chars) for log correlation."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def _write_log(entry: Dict[str, Any]) -> None:
    """Append a JSON line to the daily LiteLLM log file."""
    safe_mkdirs(LOG_DIR)
    log_file = LOG_DIR / f"litellm_calls_{_timestamp()[:10]}.jsonl"
    with log_file.open("a", encoding="utf-8") as fh:
        json.dump(entry, fh, ensure_ascii=False)
        fh.write("\n")


# --------------------------------------------------------------------------- #
# 6. Public API
# --------------------------------------------------------------------------- #
def call_llm(
    prompt: str,
    *,
    model: str | None = None,
    language: str,
    timeout: int = LLM_TIMEOUT,
    max_retries: int = MAX_RETRIES,
    temperature: float = TEMPERATURE,
) -> Dict[str, str]:
    """
    Send ``prompt`` to an LLM via LiteLLM and return a dict {cell_id: translation}.

    Parameters
    ----------
    prompt : str
        Ready-to-send prompt (already includes instructions & payload).
    model : str | None
        LiteLLM model string (e.g., "openai/gpt-4o"). If None, uses DEFAULT_MODEL.
    language : str
        Target language code for logging.
    timeout : int
        Seconds before request timeout.
    max_retries : int
        Number of retry attempts on rate-limit/server errors.
    temperature : float
        Model temperature.

    Raises
    ------
    RuntimeError
        On invalid JSON or if all retries fail.
    """
    global _last_prompt_snapshot
    _last_prompt_snapshot = prompt

    if model is None:
        model = DEFAULT_MODEL

    attempt = 0
    delay = 2  # seconds, exponential backoff
    start_time = time.time()

    # Decide whether to force Responses API
    force_responses = (
        USE_RESPONSES_API
        or (model.startswith("openai/") and os.environ.get("OPENAI_API_KEY", "").startswith("sk-proj-"))
    )

    while True:
        attempt += 1

        global _printed_prompt_once
        if PRINT_FIRST_PROMPT and not _printed_prompt_once:
            print("\n================ PROMPT SENT TO LLM =================")
            print(prompt)
            print("=====================================================\n")
            _printed_prompt_once = True

        try:
            # ---------------------- Call the model ---------------------- #
            if force_responses:
                # OpenAI Responses API path
                response = litellm.responses(
                    model=model,
                    input=prompt,
                    timeout=timeout,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                # Extract text
                if hasattr(response, "output_text") and response.output_text:
                    raw_text = response.output_text
                elif hasattr(response, "output") and response.output:
                    try:
                        raw_text = response.output[0].content[0].text
                    except Exception:
                        raw_text = str(response)
                elif isinstance(response, dict):
                    raw_text = response.get("output_text") or str(response)
                else:
                    raw_text = str(response)

                # Usage (best effort)
                usage_prompt = getattr(response, "prompt_tokens", None)
                usage_completion = getattr(response, "completion_tokens", None)

            else:
                # Legacy Chat Completions path
                response = litellm.completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Respond ONLY with a JSON object. No additional text."},
                        {"role": "user", "content": prompt},
                    ],
                    timeout=timeout,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                # Extract text
                if isinstance(response, dict):
                    raw_text = response["choices"][0]["message"]["content"].strip()
                    usage_prompt = response.get("usage", {}).get("prompt_tokens")
                    usage_completion = response.get("usage", {}).get("completion_tokens")
                elif hasattr(response, "choices") and response.choices:
                    raw_text = response.choices[0].message.content.strip()
                    usage = getattr(response, "usage", None)
                    if usage:
                        usage_prompt = getattr(usage, "prompt_tokens", None)
                        usage_completion = getattr(usage, "completion_tokens", None)
                    else:
                        usage_prompt = usage_completion = None
                else:
                    raw_text = str(response).strip()
                    usage_prompt = usage_completion = None

            # ---------------------- Parse JSON -------------------------- #
            raw_text = extract_json_payload(raw_text)
            raw_text = raw_text.replace("\n", " ")  # guard against bare newlines in JSON
            # Auto-escape any unescaped internal quotes to help JSON parsing
            raw_text = escape_unescaped_quotes(raw_text)

            global _printed_response_once
            if PRINT_FIRST_RESPONSE and not _printed_response_once:
                print("\n================ RAW LLM RESPONSE ===================")
                print(raw_text)
                print("=====================================================\n")
                _printed_response_once = True

            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(raw_text)
                except Exception as err:
                    raise ValueError("Model output is not a valid JSON object.") from err

            if not isinstance(parsed, dict):
                raise ValueError("Model output is not a JSON object.")

            # ---------------------- Success: log & return ---------------- #
            latency_ms = int((time.time() - start_time) * 1000)
            _write_log(
                {
                    "timestamp": _timestamp(),
                    "response": parsed,
                    "model": model,
                    "temperature": temperature,
                    "language": language,
                    "prompt_hash": _sha8(prompt),
                    "input_tokens": usage_prompt,
                    "output_tokens": usage_completion,
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
            delay *= 2  # backoff

        except ValueError as err:
            # Model answered but not JSON => log and try one-shot repair
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
                    "raw_output_excerpt": (raw_text[:2000] + "…") if isinstance(raw_text, str) else "n/a",
                }
            )
            # Attempt one-shot repair
            try:
                repair_prompt = (
                    "The following string is meant to be a JSON object but contains invalid syntax. "
                    "Please correct any formatting issues (e.g., unescaped quotes) and respond ONLY with the valid JSON object.\n\n"
                    f"{raw_text}"
                )
                repair_response = litellm.completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a JSON validator and fixer."},
                        {"role": "user", "content": repair_prompt},
                    ],
                    timeout=timeout,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
                repaired_text = repair_response["choices"][0]["message"]["content"].strip()
                repaired_text = escape_unescaped_quotes(repaired_text)
                parsed = json.loads(repaired_text)

                _write_log(
                    {
                        "timestamp": _timestamp(),
                        "response": parsed,
                        "model": model,
                        "temperature": temperature,
                        "language": language,
                        "prompt_hash": _sha8(prompt),
                        "input_tokens": usage_prompt,
                        "output_tokens": usage_completion,
                        "latency_ms": int((time.time() - start_time) * 1000),
                        "status": "repaired_json",
                        "attempt": attempt,
                    }
                )
                return parsed
            except Exception as repair_err:
                raise RuntimeError("Model returned invalid JSON and repair attempt failed.") from repair_err

        except Exception as err:  # pragma: no cover
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





# --- One-time footer debug print (on import) ---
_api_head = os.environ.get("OPENAI_API_KEY", "")[:15]
print(f"[litellm_client] OPENAI_API_KEY[0:15]: '{_api_head}...'")
print("---Litellm script executed---")
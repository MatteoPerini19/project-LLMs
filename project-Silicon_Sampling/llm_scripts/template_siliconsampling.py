"""
template_siliconsampling.py
───────────────────────────
Run many parallel LLM calls (“silicon sampling”) and append the outputs
to a JSONL file for downstream statistical analysis.

This script relies on the helper utilities defined in
`functions_parallel_calls.py` (same folder).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from dotenv import load_dotenv

from functions_parallel_calls import asynch_completion, _extract_json_payload

# import litellm; litellm._turn_on_debug()   # turns on litellm debugging mode 

ROOT_DIR = Path(__file__).resolve().parents[2]   # …/project-LLMs
PROMPTS_DIR = ROOT_DIR / "project-Silicon_Sampling" / "llm_prompts"
OUTPUT_DIR  = ROOT_DIR / "project-Silicon_Sampling" / "llm_outputs"
load_dotenv(ROOT_DIR / ".env", override=True)

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
SUFFIX = "_2"          # managed by llm_orchestrator.py

PROMPT_PATH = PROMPTS_DIR / f"prompt{SUFFIX}.txt"           # prompt file
OUTPUT_PATH = OUTPUT_DIR / f"output_memory{SUFFIX}.jsonl"  # where results are stored

MODEL = "gemini/gemini-2.5-flash"   # gemini/gemini-2.5-flash   # openai/gpt-4o
NUM_CALLS = 60
CONCURRENCY = 15              # simultaneous in‑flight requests
MAX_TOKENS = None             # leave None for model default

# ──────────────────────────────────────────────────────────────
# Fail test
# ──────────────────────────────────────────────────────────────

import os, sys
if not os.getenv("OPENAI_API_KEY"):
    sys.exit("❌ OPENAI_API_KEY missing — check .env or shell variables.")
if not os.getenv("GEMINI_API_KEY"):
    sys.exit("❌ GEMINI_API_KEY missing — check .env or shell variables.")

# ──────────────────────────────────────────────────────────────
# Load prompt
# ──────────────────────────────────────────────────────────────
with PROMPT_PATH.open(encoding="utf-8") as pf:
    prompt = pf.read().strip()

messages = [{"role": "user", "content": prompt}]

# ──────────────────────────────────────────────────────────────
# Fire parallel completions
# ──────────────────────────────────────────────────────────────
results = asynch_completion(
    num_calls=NUM_CALLS,
    messages=messages,
    model=MODEL,
    max_tokens=MAX_TOKENS,
    concurrency=CONCURRENCY,
)

# Ensure output directory exists
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────
# Persist each response
# ──────────────────────────────────────────────────────────────
for res in results:
    if isinstance(res, Exception):
        print("❌ Exception during completion:", res)
        continue

    out_text = (res.choices[0].message.content or "").strip()
    print("🔹 Output:\n", out_text, "\n")

    # Clean & parse JSON content if present
    clean_out = _extract_json_payload(out_text)

    # ``clean_out`` may already be a dict/list if the helper succeeded.
    if isinstance(clean_out, str):
        try:
            parsed_out = json.loads(clean_out)
        except json.JSONDecodeError:
            parsed_out = clean_out  # keep raw string if still not valid JSON
    else:
        parsed_out = clean_out

    record = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "response_json": parsed_out,   # dict/list if JSON, else raw string
        "response_raw": out_text,      # verbatim text
        "prompt": prompt,
        "model": res.model,
        "prompt_tokens": res.usage.prompt_tokens,
        "completion_tokens": res.usage.completion_tokens,
        "total_tokens": res.usage.total_tokens,
    }

    with OUTPUT_PATH.open("a", encoding="utf-8") as fout:
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\n\n✔ Done. Results appended to {OUTPUT_PATH}")

# ──────────────────────────────────────────────────────────────
# Quick summary: number of records in the JSONL file
# ──────────────────────────────────────────────────────────────

print(PROMPT_PATH)

try:
    with OUTPUT_PATH.open("r", encoding="utf-8") as _f:
        line_count = sum(1 for _ in _f if _.strip())
    print(f"\n\n🔸 Total records in {OUTPUT_PATH.name}: {line_count}")
except FileNotFoundError:
    print(f"\n\n⚠️ Cannot count lines – file {OUTPUT_PATH} not found.")
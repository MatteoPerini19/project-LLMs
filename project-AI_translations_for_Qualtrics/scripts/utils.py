"""
utils.py
========
Assorted one‑liner helpers shared across the Qualtrics translation
pipeline.  Keep this file *tiny*—helpers used by just one module belong
in that module.

Functions
---------
safe_mkdirs(*paths)
    Recursively create each Path if it does not yet exist.

sanitize_json_dict(raw, *, expected_keys)
    Parse the LLM’s JSON output, verify it matches the skeleton, and
    return a clean ``dict[str, str]``.

normalize_whitespace(text)
    Collapse duplicate spaces / newlines while preserving inside‑tag
    spacing.

detect_image_only(text)
    True if the cell contains nothing but a single <img …> tag.

rapidfuzz_ratio(a, b)
    Fast similarity score in [0, 1] using RapidFuzz’s *ratio*.

get_timestamp()
    ISO‑8601 UTC time with millisecond precision—handy for filenames.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from rapidfuzz.fuzz import ratio


# --------------------------------------------------------------------------- #
# Filesystem helpers
# --------------------------------------------------------------------------- #


def safe_mkdirs(*paths: Path | str) -> None:
    """
    Create each *path* (recursively) if it does not exist.

    Accepts both ``Path`` and ``str`` arguments.  Silently does nothing if
    the directory already exists.
    """
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# String sanitation
# --------------------------------------------------------------------------- #


_WHITESPACE_RE = re.compile(r"[ \t\r\n]+")


def normalize_whitespace(text: str) -> str:
    """
    Collapse internal runs of whitespace into a single space and strip
    leading/trailing blanks.  HTML tags and entities are left intact.
    """
    return _WHITESPACE_RE.sub(" ", text).strip()



_IMG_ONLY_RE = re.compile(r"^\s*<img\b[^>]*>\s*$", re.IGNORECASE | re.DOTALL)


# --------------------------------------------------------------------------- #
# Helper to auto-escape unescaped double quotes in JSON-like strings
# --------------------------------------------------------------------------- #

def escape_unescaped_quotes(s: str) -> str:
    """
    Auto-escape any unescaped double quotes inside JSON-like strings
    (e.g., values with internal quotes), so that JSON parsing succeeds.
    """
    return re.sub(
        r'(:\s*")([^"]*?)(")',
        lambda m: m.group(1) + m.group(2).replace('"', '\\"') + m.group(3),
        s,
    )


def detect_image_only(text: str) -> bool:
    """
    Return *True* if *text* contains only a single <img …> tag and no
    other visible characters.
    """
    return bool(_IMG_ONLY_RE.match(text))


# --------------------------------------------------------------------------- #
# JSON guardrails
# --------------------------------------------------------------------------- #


def sanitize_json_dict(
    raw: str | Mapping[str, str],
    *,
    expected_keys: Iterable[str],
) -> dict[str, str]:
    """
    Parse *raw* (str or already‑decoded dict) and ensure it matches
    *expected_keys* exactly.

    Raises
    ------
    ValueError
        If the JSON cannot be parsed, is not a dict, or keys mismatch.
    """
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM output is not valid JSON.") from exc
    elif isinstance(raw, Mapping):
        payload = dict(raw)  # shallow copy
    else:
        raise ValueError("LLM output is neither str nor dict.")

    exp = set(expected_keys)
    got = set(payload.keys())
    if got != exp:
        missing = ", ".join(sorted(exp - got))
        extra = ", ".join(sorted(got - exp))
        raise ValueError(
            f"JSON keys mismatch. Missing: [{missing}]  Extra: [{extra}]"
        )

    # Coerce values to str and normalize whitespace
    return {k: normalize_whitespace(str(v)) for k, v in payload.items()}


# --------------------------------------------------------------------------- #
# Similarity metric
# --------------------------------------------------------------------------- #


def rapidfuzz_ratio(a: str, b: str) -> float:
    """
    Normalized RapidFuzz ratio in [0, 1].

    Example
    -------
    >>> rapidfuzz_ratio("hello", "h3llo")
    0.8
    """
    return ratio(a, b) / 100.0


# --------------------------------------------------------------------------- #
# Timestamps
# --------------------------------------------------------------------------- #


def get_timestamp() -> str:
    """
    Return current UTC time as ISO‑8601 string ``YYYY-MM-DDTHH:MM:SS.mmmZ``.
    """
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


# --------------------------------------------------------------------------- #
# JSON payload extractor
# --------------------------------------------------------------------------- #


def extract_json_payload(text: str) -> str:
    """
    Isolate the JSON portion of *text* so that ``json.loads`` succeeds even
    if the model wrapped the object in ```json fences or sprinkled curly
    quotes.

    Parameters
    ----------
    text : str
        Raw LLM output that should contain a JSON object.

    Returns
    -------
    str
        Clean string starting with '{' and ending with '}' (best effort).
    """
    import re

    t = text.strip()

    # Remove ```json ... ``` fences
    if t.startswith("```"):
        m = re.match(r"```(?:json)?\s*(.*?)\s*```", t, flags=re.DOTALL)
        if m:
            t = m.group(1).strip()

    # Trim leading / trailing garbage before first { and after last }
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1:
        t = t[start : end + 1]

    # Replace curly quotes with straight ones
    return (
        t.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )


# --------------------------------------------------------------------------- #
# Update exported names
# --------------------------------------------------------------------------- #

__all__ = [
    "safe_mkdirs",
    "sanitize_json_dict",
    "normalize_whitespace",
    "detect_image_only",
    "rapidfuzz_ratio",
    "get_timestamp",
    "extract_json_payload",
    "escape_unescaped_quotes",
]



print("---Utils script executed---")
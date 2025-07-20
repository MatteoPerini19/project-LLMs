"""
canned_loader.py
================
Utilities for reading and querying the *canned* translation dictionary
(`canned_translations.json`).  These translations are “hard‑coded” by the
researcher and **must never be overridden** by the LLM.

Public API
----------
load_canned_dict(path: Path | str, *, normalize: bool = True) -> dict
    Read the JSON file and return a two‑level dict
    ``{english_text -> {lang_code -> translation}}``.

get_canned(english: str, lang: str, table: dict) -> str | None
    Single lookup helper.  Returns the canned translation or *None*.

normalize_text(text: str) -> str
    Minimal whitespace/punctuation normalization so that look‑ups are
    deterministic.

This module is intentionally free of logging and LiteLLM imports.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Mapping

from config import CANNED_DICT_PATH

# --------------------------------------------------------------------------- #
# Normalization helpers
# --------------------------------------------------------------------------- #

_WS_RE = re.compile(r"[ \t\r\n]+")


def normalize_text(text: str) -> str:
    """
    Cheap canonicalization: collapse internal whitespace and strip
    leading/trailing blanks.  Does **not** lowercase so that proper
    nouns remain intact.
    """
    return _WS_RE.sub(" ", text).strip()


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #


def load_canned_dict(
    path: str | Path = CANNED_DICT_PATH,
    *,
    normalize: bool = True,
) -> Dict[str, Dict[str, str]]:
    """
    Load *canned_translations.json*.

    The JSON file must have the shape::

        {
            "I would buy this": {
                "it": "Lo comprerei",
                "de": "Ich würde es kaufen"
            },
            "Second-hand": {
                "it": "Usato",
                "de": "Secondhand"
            }
        }

    Parameters
    ----------
    path : str | Path, optional
        Location of the JSON file.  Defaults to ``config.CANNED_DICT_PATH``.
    normalize : bool, optional
        If *True*, run :func:`normalize_text` on every English key.

    Returns
    -------
    dict
        Two-level dictionary ``{english -> {lang_code -> translation}}``.
        Empty dict if the file is missing or empty.

    Raises
    ------
    ValueError
        If the JSON is malformed or has the wrong structure.
    """
    p = Path(path)
    if not p.exists():
        return {}

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"canned_translations.json is not valid JSON: {exc}") from exc

    if not isinstance(raw, Mapping):
        raise ValueError("canned_translations.json must contain a JSON object at top")

    table: Dict[str, Dict[str, str]] = {}
    for eng, bundle in raw.items():
        if not isinstance(bundle, Mapping):
            raise ValueError(f"Value for '{eng}' must be an object, got {type(bundle)}")
        key = normalize_text(eng) if normalize else str(eng)
        table[key] = {k: str(v) for k, v in bundle.items()}

    return table


# --------------------------------------------------------------------------- #
# Lookup
# --------------------------------------------------------------------------- #


def get_canned(
    english: str,
    lang: str,
    table: Mapping[str, Dict[str, str]],
    *,
    normalize: bool = True,
) -> str | None:
    """
    Retrieve the canned translation for *english* in target *lang*.

    Parameters
    ----------
    english : str
        The English source string to look up.
    lang : str
        ISO‑639‑1 language code.
    table : dict
        The dictionary returned by :func:`load_canned_dict`.
    normalize : bool, optional
        Normalize the *english* key first (default: True).

    Returns
    -------
    str | None
        The translation if found; otherwise *None*.
    """
    key = normalize_text(english) if normalize else english
    return table.get(key, {}).get(lang)

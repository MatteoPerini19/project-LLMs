"""
translation_memory.py
=====================
Incremental, disk‑backed cache so identical English strings are never
re‑translated (and identical → identical guarantee is enforced).

The cache file lives at ``data/tmp_cache.jsonl`` and is a *JSON Lines*
file where each line has the schema::

    {
      "en":  "I would buy this even second‑hand",
      "lang": "it",
      "translation": "Lo comprerei anche di seconda mano"
    }

Public API
----------
load_cache(path) -> dict
    Read / create the cache.  Returns ``{english -> {lang -> text}}``.

update_cache(cache, new_block, lang, path) -> None
    Merge a dict ``{english_text → translated_text}`` into both the
    in‑memory cache and the on‑disk JSONL file.

lookup_exact(english, lang, cache) -> str | None
    O(1) retrieval helper used by orchestrator.

find_near_duplicates(text, cache, threshold=0.92) -> list[str]
    Utility for audit; RapidFuzz similarity search over the English keys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

from rapidfuzz import process, fuzz
from filelock import FileLock

from utils import normalize_text, safe_mkdirs

# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #


def load_cache(path: Path) -> Dict[str, Dict[str, str]]:
    """
    Load an existing translation cache or return an empty dict.

    Parameters
    ----------
    path : Path
        Location of ``tmp_cache.jsonl``.

    Returns
    -------
    dict
        Nested mapping ``{english_text -> {lang_code -> translation}}``.
    """
    if not path.exists():
        safe_mkdirs(path.parent)
        return {}

    memory: Dict[str, Dict[str, str]] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                en = normalize_text(rec["en"])
                lang = rec["lang"]
                text = rec["translation"]
            except (json.JSONDecodeError, KeyError):
                # Skip corrupt line
                continue

            memory.setdefault(en, {})[lang] = text
    return memory


# --------------------------------------------------------------------------- #
# Update
# --------------------------------------------------------------------------- #


def update_cache(
    cache: Dict[str, Dict[str, str]],
    new_block: Mapping[str, str],
    lang: str,
    path: Path,
) -> None:
    """
    Append *new_block* to cache on disk and merge into in‑memory dict.

    A file‑lock is used so that concurrent processes do not corrupt the
    JSONL file.

    Parameters
    ----------
    cache : dict
        In‑memory dictionary returned by :func:`load_cache`.
    new_block : Mapping[str, str]
        Mapping *english_text → translated_text* for this batch.
    lang : str
        Target language code.
    path : Path
        Location of the JSONL cache file.
    """
    safe_mkdirs(path.parent)
    lock = FileLock(str(path) + ".lock")

    with lock:  # guarantees atomic append across processes
        with path.open("a", encoding="utf-8") as fh:
            for en_text, target_text in new_block.items():
                en_key = normalize_text(en_text)
                # merge in‑memory
                cache.setdefault(en_key, {})[lang] = target_text
                # append on disk
                fh.write(
                    json.dumps(
                        {
                            "en": en_key,
                            "lang": lang,
                            "translation": target_text,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )


# --------------------------------------------------------------------------- #
# Lookup helpers
# --------------------------------------------------------------------------- #


def lookup_exact(
    english: str,
    lang: str,
    cache: Mapping[str, Dict[str, str]],
) -> str | None:
    """
    Return cached translation if present; else *None*.
    """
    key = normalize_text(english)
    return cache.get(key, {}).get(lang)


def find_near_duplicates(
    text: str,
    cache: Mapping[str, Dict[str, str]],
    *,
    threshold: float = 0.92,
    limit: int = 5,
) -> List[str]:
    """
    RapidFuzz search for near-duplicate English strings in the cache.

    Returns a list of English keys whose similarity >= threshold.
    """
    choices: Iterable[str] = cache.keys()
    matches = process.extract(
        text,
        choices,
        scorer=fuzz.ratio,
        score_cutoff=int(threshold * 100),
        limit=limit,
    )
    return [item for item, _score, _ in matches]


__all__ = [
    "load_cache",
    "update_cache",
    "lookup_exact",
    "find_near_duplicates",
]


print("---Memory script executed---")
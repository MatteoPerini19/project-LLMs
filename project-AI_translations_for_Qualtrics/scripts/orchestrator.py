"""
orchestrator.py
================
Main CLI driver for the AI‑powered Qualtrics translation pipeline.

Workflow
--------
1.  Load configuration (API keys, model name, batch size) from ``scripts/config.py``.
2.  Read the Qualtrics translation CSV into a pandas DataFrame.
3.  For each *target language* requested on the command line:
    a. Walk through the rows in **batches**.
    b. For each item, consult *canned translations* first, then the
       *translation memory* cache.  Items still lacking a translation
       are bundled and sent to the LLM.
    c. Update the DataFrame and the cache with new translations.
4.  Optionally run the *fuzzy‑duplicate audit*.
5.  Persist:
    • filled CSV under ``outputs/translated_csv/``  
    • log of every LiteLLM call under ``outputs/logs/``  
    • updated cache under ``data/tmp_cache.jsonl``

This module contains **no model‑specific code**; that is delegated to
``litellm_client.py``.  Likewise, all constant paths & hyper‑parameters
live in ``config.py`` so the orchestrator stays slim.
 """

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from tqdm import tqdm

# Internal imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(SCRIPT_DIR))  # allow "python -m scripts.orchestrator"

from config import (  # noqa: E402
    BATCH_SIZE,
    CACHE_PATH,
    CANNED_DICT_PATH,
    INPUT_DIR,
    LOG_DIR,
    MODEL_NAME,
    OUTPUT_DIR,
    PROMPT_TEMPLATE_PATH,
    DEFAULT_LANGS,
)
from canned_loader import load_canned_dict  # noqa: E402
from litellm_client import call_llm  # noqa: E402
from translation_memory import load_cache, update_cache, lookup_exact  # noqa: E402
from utils import safe_mkdirs, sanitize_json_dict, detect_image_only  # noqa: E402

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def build_cell_ids(df: pd.DataFrame) -> pd.Series:
    """
    Ensure the DataFrame has a stable 'cell_id' column.

    If the CSV already contains a column named 'cell_id', we respect it.
    Otherwise we fabricate IDs row-wise as 'ROW_<index>'.

    Returns
    -------
    pd.Series
        The Series of cell identifiers.
    """
    if "cell_id" in df.columns:
        return df["cell_id"]
    # Fabricate IDs
    fabricated = [f"ROW_{i}" for i in range(len(df))]
    df.insert(0, "cell_id", fabricated)
    return df["cell_id"]


def batch_indices(total_len: int, batch_size: int):
    """
    Yield (start, stop) tuples covering `total_len` in strides of `batch_size`.
    """
    for start in range(0, total_len, batch_size):
        yield start, min(start + batch_size, total_len)


def build_prompt(
    template: str,
    language: str,
    items: List[Tuple[str, str]],
) -> Tuple[str, Dict[str, str]]:
    """
    Populate the prompt template for a single LLM call.

    Parameters
    ----------
    template : str
        The raw prompt template with placeholders ``{language}``,
        ``{skeleton}``, and ``{payload_lines}``.
    language : str
        ISO‑639‑1 code of the target language.
    items : list of (cell_id, english_text)
        The lines that still need translating.

    Returns
    -------
    prompt : str
        The ready‑to‑send prompt string.
    skeleton : dict
        The dict ``cell_id -> ""`` used for JSON validation later.
    """
    skeleton = {cid: "" for cid, _ in items}
    skeleton_json = json.dumps(skeleton, ensure_ascii=False)
    payload_lines = "\n".join(f"{cid} || {txt}" for cid, txt in items)
    prompt = template.format(
        language=language, skeleton=skeleton_json, payload_lines=payload_lines
    )
    return prompt, skeleton


def apply_translations(
    df: pd.DataFrame,
    translations: Dict[str, str],
    language: str,
):
    """
    Merge a set of translations back into the DataFrame in‑place.

    Parameters
    ----------
    df : DataFrame
        The survey translation table, must include 'cell_id'.
    translations : dict
        Mapping *cell_id → translated_text*.
    language : str
        Target language column to update.
    """
    for cid, translated in translations.items():
        df.loc[df["cell_id"] == cid, language] = translated


# --------------------------------------------------------------------------- #
# Main routine
# --------------------------------------------------------------------------- #


def main(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Pipeline orchestrator for Qualtrics AI translations."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_DIR / "Qualtrics_translations.csv",
        help="CSV file exported from Qualtrics with all language columns.",
    )
    parser.add_argument(
        "--langs",
        type=str,
        default=",".join(DEFAULT_LANGS),
        help=("Comma‑separated ISO‑639‑1 codes of target languages. "
              f"Default: {','.join(DEFAULT_LANGS)}"),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Items per LLM call (default {BATCH_SIZE})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=MODEL_NAME,
        help=f"Model name (default {MODEL_NAME})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and log but don’t write files or hit the LLM.",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Run the fuzzy‑duplicate audit at the end.",
    )

    args = parser.parse_args(argv)

    # ------------------------------------------------------------------- #
    # I/O guards
    # ------------------------------------------------------------------- #
    if not args.input.exists():
        parser.error(f"Input file not found: {args.input}")
    safe_mkdirs(OUTPUT_DIR, LOG_DIR, CACHE_PATH.parent)

    # ------------------------------------------------------------------- #
    # Load resources
    # ------------------------------------------------------------------- #
    df = pd.read_csv(args.input, dtype=str).fillna("")
    build_cell_ids(df)
    canned = load_canned_dict(CANNED_DICT_PATH)
    cache = load_cache(CACHE_PATH)
    with open(PROMPT_TEMPLATE_PATH, encoding="utf-8") as fh:
        prompt_template = fh.read()

    langs = [code.strip() for code in args.langs.split(",") if code.strip()]

    # ------------------------------------------------------------------- #
    # Main loop
    # ------------------------------------------------------------------- #
    for lang in tqdm(langs, desc="Languages", unit="lang"):
        tqdm.write(f"\n=== Processing language: {lang} ===")
        if lang not in df.columns:
            df[lang] = ""

        rows_to_translate = df[df[lang].str.strip() == ""]
        if rows_to_translate.empty:
            tqdm.write(f"All items already translated for {lang}. Skipping.")
            continue

        # Iterate in batches
        row_idxs = rows_to_translate.index.tolist()
        for start, stop in tqdm(
            list(batch_indices(len(row_idxs), args.batch_size)),
            desc=f"{lang} batches",
            unit="batch",
        ):
            batch_idx = row_idxs[start:stop]
            sub_df = df.loc[batch_idx]

            cid_to_en = dict(zip(sub_df["cell_id"], sub_df["en"]))

            # Collector: cid -> translated text
            ready_translations = {}

            # Step 1: canned dictionary
            for cid, eng in zip(sub_df["cell_id"], sub_df["en"]):
                if eng in canned and lang in canned[eng]:
                    ready_translations[cid] = canned[eng][lang]

            # Step 2: exact cache (English‑keyed)
            for cid, eng in cid_to_en.items():
                if cid in ready_translations:
                    continue
                cached = lookup_exact(eng, lang, cache)
                if cached:
                    ready_translations[cid] = cached

            # Step 3: remaining items -> LLM
            remaining_items = [
                (cid, eng)
                for cid, eng in zip(sub_df["cell_id"], sub_df["en"])
                if cid not in ready_translations and not detect_image_only(eng)
            ]

            if remaining_items and not args.dry_run:
                prompt, skeleton = build_prompt(
                    prompt_template, lang, remaining_items
                )
                response_json = call_llm(
                    prompt, model=args.model, language=lang
                )
                translated_block = sanitize_json_dict(
                    response_json, expected_keys=skeleton.keys()
                )
                ready_translations.update(translated_block)
                # Update cache with EN‑key mapping
                en_to_translation = {
                    cid_to_en[cid]: txt for cid, txt in translated_block.items()
                }
                update_cache(cache, en_to_translation, lang, CACHE_PATH)

            # Merge all obtained translations back into df
            apply_translations(df, ready_translations, lang)

    # ------------------------------------------------------------------- #
    # Save outputs
    # ------------------------------------------------------------------- #
    output_name = args.input.stem + "_filled.csv"
    out_path = OUTPUT_DIR / output_name
    if not args.dry_run:
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        tqdm.write(f"✅ Saved translated file → {out_path}")

    # Optionally run audit
    if args.audit and not args.dry_run:
        try:
            from audit_fuzzy_matches import run_audit  # lazy import

            report_path = run_audit(df)
            tqdm.write(f"🔍 Audit report written to {report_path}")
        except ImportError as exc:
            tqdm.write(f"⚠️  Audit skipped (import error: {exc})")


if __name__ == "__main__":
    main()

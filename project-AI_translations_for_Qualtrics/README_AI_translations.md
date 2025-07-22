# AI Translations for Qualtrics

A Python pipeline that fills a Qualtrics “Translation Export” CSV in multiple target languages using:

1. **Canned dictionary**
   Deterministic strings you specify in `data/canned_translations.json` (e.g., Likert anchors, UI labels).

2. **Translation memory**
   Re-uses any English→Translation pairs stored in `data/tmp_cache.jsonl` from prior runs.

3. **LLM batch calls**
   Sends only the remaining empty cells to an LLM (ChatGPT, Gemini, etc.) in JSON‑mode, parses and validates the response, auto‑repairs any minor formatting issues, and ensures proper escaping.

Each batch is checkpointed to disk so you can safely resume after an interruption.

---

## Overview

**AI Translations for Qualtrics** combines three layers to produce consistent, context‑aware translations:

| Layer              | Purpose                                    |
| ------------------ | ------------------------------------------ |
| Canned dictionary  | Fixed translations (e.g., scale anchors)   |
| Translation memory | Cache of previous translations             |
| LLM batch calls    | Context‑aware translation via JSON prompts |

### Quick Start

```bash
# 1. Clone repo and set up venv
cd project-LLMs
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Command-line Execution

```bash
# activate the venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate

# first-time dependency install
pip install -r requirements.txt

# sanity-check (no writes, no API calls)
python -m project-AI_translations_for_Qualtrics.scripts.orchestrator \
       --input project-AI_translations_for_Qualtrics/data/input/Qualtrics_translations.csv \
       --dry-run

# real run (defaults: it, pt-br, tr, es-es, sv, nl)
python -m project-AI_translations_for_Qualtrics.scripts.orchestrator \
       --input project-AI_translations_for_Qualtrics/data/input/Qualtrics_translations.csv
```

At completion, the translated CSV is at `outputs/translated_csv/Qualtrics_translations_filled.csv`.

---

## Prerequisites and Folder Layout

```text
project-LLMs/
├── .venv/                          # virtual environment
├── .env                            # API keys (git‑ignored)
├── .gitignore                      # ignores .env, tmp_cache.jsonl, __pycache__/
├── requirements.txt                # pip install -r requirements.txt
└── project-AI_translations_for_Qualtrics/
    ├── README_AI_translations.md   # this file
    ├── prompt_AI_translation_instructions.txt
    ├── data/
    │   ├── input/Qualtrics_translations.csv
    │   ├── canned_translations.json
    │   └── tmp_cache.jsonl
    ├── outputs/
    │   ├── translated_csv/Qualtrics_translations_filled.csv
    │   ├── logs/litellm_calls_YYYY-MM-DD.jsonl
    │   └── reports/ambiguous_items.xlsx
    └── scripts/
        ├── config.py
        ├── orchestrator.py
        ├── litellm_client.py
        ├── translation_memory.py
        ├── canned_loader.py
        ├── audit_fuzzy_matches.py
        └── utils.py
```

---

## Customizable Parameters

| Parameter                  | Location                  | Default                   | Description                                 |
| :------------------------- | :------------------------ | :------------------------ | :------------------------------------------ |
| **MODEL\_NAME**            | `scripts/config.py`       | `openai/gpt-4o`           | LLM identifier for LiteLLM.                 |
| **BATCH\_SIZE**            | `scripts/config.py` / CLI | `10`                      | Items per LLM call (`--batch-size`).        |
| **LLM\_TIMEOUT**           | `scripts/config.py`       | `120`                     | Seconds to wait for each API call.          |
| **TEMPERATURE**            | `scripts/config.py`       | `0.0`                     | Sampling temperature (0 = deterministic).   |
| **MAX\_RETRIES**           | `scripts/config.py`       | `4`                       | Retry attempts on API failure.              |
| **PRINT\_FIRST\_PROMPT**   | `scripts/config.py`       | `False`                   | Print first prompt to stdout for debugging. |
| **PRINT\_FIRST\_RESPONSE** | `scripts/config.py`       | `False`                   | Print first LLM response for debugging.     |
| **USE\_RESPONSES\_API**    | `scripts/config.py`       | `True`                    | Use OpenAI Responses endpoint if available. |
| **DEFAULT\_LANGS**         | `scripts/config.py` / CLI | `IT,PT-BR,TR,ES-ES,SV,NL` | Default languages when `--langs` omitted.   |
| **EN\_COL**                | `scripts/config.py` / CLI | `EN`                      | Column name for English source text.        |

---

## Workflow Details

1. **Load CSV & Prepare**
   Read input, generate `cell_id` if missing.

2. **Canned & Cache Pass**
   Fill from `canned_translations.json` then `tmp_cache.jsonl`.

3. **LLM Batch Translation**

   * Build prompt with:

     * Study summary and glossary (≈1k tokens) from prompt file.
     * JSON skeleton of empty cells.
     * Payload lines `cell_id || English text`.
   * Call `litellm_client.call_llm()`: extract JSON, auto-escape quotes, parse, repair if needed.

4. **Checkpoint**

   * Update DataFrame and write partial CSV.
   * Append new entries to `tmp_cache.jsonl`.
   * Log each call in `outputs/logs/` with full response and metrics.

5. **Optional Audit**
   Generate `ambiguous_items.xlsx` highlighting near-duplicate English items.

---

## Resume & Recovery

Rerun the orchestrator with the same parameters. Completed cells and cached translations are skipped automatically.

---

## Troubleshooting

* **401 Unauthorized**: verify `.env` API keys.
* **invalid\_json** in logs: check quoting rules in prompt and auto-escape logic.
* **Slow batches**: reduce `BATCH_SIZE`.
* **Divergent duplicates**: run with `--audit` and adjust `canned_translations.json`.

---

For deeper investigation, refer to inline docstrings in `project-AI_translations_for_Qualtrics/scripts/`.

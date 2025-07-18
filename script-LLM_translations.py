"""
translate_qualtrics.py
Automates multi‑language Qualtrics translation with LiteLLM/GPT‑4o.
Note: it is recommended to either translate manually or add to the "Canned" dictionary all redundant parts of the survey. This ensures they are translated consistently across the survey. 

Author: <you>
Date  : 2025‑07‑05
"""




#TODO: 
# AGGIUNGI: NO TRADUZIONE PER NUMERI 



from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List
import sys 

import pandas as pd
from dotenv import load_dotenv

import litellm

# ---------------------------------------------------------------------
# Load environment variables and validate API keys
# ---------------------------------------------------------------------
load_dotenv()  # Reads `.env` in project root, containing API keys 

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

if not OPENAI_API_KEY:
    raise EnvironmentError(
        "OPENAI_API_KEY not found. Add it to your .env or export it before running."
    )

# GEMINI_API_KEY is optional if GPT is used wq
if GEMINI_API_KEY is None:
    print("⚠️  GEMINI_API_KEY not set – Gemini fallback disabled.")


# ---------------------------------------------------------------------
# 0. Configuration – edit here if needed
# ---------------------------------------------------------------------
INPUT_FILE      = Path("SHC_qualtrics_translations.xlsx")  
OUTPUT_FILE     = Path("SHC_qualtrics_translations.output.xlsx")
SHEET_NAME      = 0                     # or the sheet label
MODEL           = "gpt-4o-mini"         # gpt-4o-mini should be the cheepes OpenAI model 
MAX_RETRIES     = 3
SLEEP_BETWEEN   = 0.6                                     
LANG_COLS       = ["IT", "PT-BR", "TR", "ES-ES", "SV", "NL"]
SOURCE_COL      = "EN"

# “Canned” translations for scale anchors & other boilerplate -------------
# Expand in case of new recurring phrases.
CANNED: Dict[str, Dict[str, str]] = {
    "Strongly disagree": {
        "IT": "Fortemente in disaccordo",
        "PT-BR": "Discordo totalmente",
        "TR": "Kesinlikle katılmıyorum",
        "ES-ES": "Totalmente en desacuerdo",
        "SV": "Håller helt inte med",
        "NL": "Helemaal mee oneens",
    },
    "Disagree": {
        "IT": "In disaccordo",
        "PT-BR": "Discordo",
        "TR": "Katılmıyorum",
        "ES-ES": "En desacuerdo",
        "SV": "Håller inte med",
        "NL": "Mee oneens",
    },
    "Somewhat disagree": {
        "IT": "",
        "PT-BR": "",
        "TR": "",
        "ES-ES": "",
        "SV": "",
        "NL": "",
    },
    "Neither agree nor disagree": {
        "IT": "Né d’accordo né in disaccordo",
        "PT-BR": "Nem concordo nem discordo",
        "TR": "Ne katılıyorum ne de katılmıyorum",
        "ES-ES": "Ni de acuerdo ni en desacuerdo",
        "SV": "Varken eller",
        "NL": "Niet mee eens, niet mee oneens",
    },
    "Agree": {
        "IT": "D’accordo",
        "PT-BR": "Concordo",
        "TR": "Katılıyorum",
        "ES-ES": "De acuerdo",
        "SV": "Håller med",
        "NL": "Mee eens",
    },
    "Somewhat agree": {
        "IT": "",
        "PT-BR": "",
        "TR": "",
        "ES-ES": "",
        "SV": "",
        "NL": "",
    },
    "Strongly agree": {
        "IT": "Fortemente d’accordo",
        "PT-BR": "Concordo totalmente",
        "TR": "Tamamen katılıyorum",
        "ES-ES": "Totalmente de acuerdo",
        "SV": "Håller helt med",
        "NL": "Helemaal mee eens",
    },
    "0": {
        "IT": "0",
        "PT-BR": "0",
        "TR": "0",
        "ES-ES": "0",
        "SV": "0",
        "NL": "0",
    },
    "1": {
        "IT": "1",
        "PT-BR": "1",
        "TR": "1",
        "ES-ES": "1",
        "SV": "1",
        "NL": "1",
    },
    "2": {
        "IT": "2",
        "PT-BR": "2",
        "TR": "2",
        "ES-ES": "2",
        "SV": "2",
        "NL": "2",
    },
    "3": {
        "IT": "3",
        "PT-BR": "3",
        "TR": "3",
        "ES-ES": "3",
        "SV": "3",
        "NL": "3",
    },
    "4": {
        "IT": "4",
        "PT-BR": "4",
        "TR": "4",
        "ES-ES": "4",
        "SV": "4",
        "NL": "4",
    },
    "5": {
        "IT": "5",
        "PT-BR": "5",
        "TR": "5",
        "ES-ES": "5",
        "SV": "5",
        "NL": "5",
    },
    "6": {
        "IT": "6",
        "PT-BR": "6",
        "TR": "6",
        "ES-ES": "6",
        "SV": "6",
        "NL": "6",
    },
    "7": {
        "IT": "7",
        "PT-BR": "7",
        "TR": "7",
        "ES-ES": "7",
        "SV": "7",
        "NL": "7",
    },
    "8": {
        "IT": "8",
        "PT-BR": "8",
        "TR": "8",
        "ES-ES": "8",
        "SV": "8",
        "NL": "8",
    },
    "9": {
        "IT": "9",
        "PT-BR": "9",
        "TR": "9",
        "ES-ES": "9",
        "SV": "9",
        "NL": "9",
    },
    "10": {
        "IT": "10",
        "PT-BR": "10",
        "TR": "10",
        "ES-ES": "10",
        "SV": "10",
        "NL": "10",
    },
    "0. Not at all": {
        "IT": "",
        "PT-BR": "",
        "TR": "",
        "ES-ES": "",
        "SV": "",
        "NL": "",
    },
    "0. Not important at all": {
        "IT": "",
        "PT-BR": "",
        "TR": "",
        "ES-ES": "",
        "SV": "",
        "NL": "",
    },
    "6. Very much": {
        "IT": "",
        "PT-BR": "",
        "TR": "",
        "ES-ES": "",
        "SV": "",
        "NL": "",
    },
    "6. Extremely important": {
        "IT": "",
        "PT-BR": "",
        "TR": "",
        "ES-ES": "",
        "SV": "",
        "NL": "",
    },
    "EXPRESSION": {
        "IT": "",
        "PT-BR": "",
        "TR": "",
        "ES-ES": "",
        "SV": "",
        "NL": "",
    },

}




# Prompt template --------------------------------------------------------
PROMPT_TEMPLATE = """
You are a strict and precise professional translator. 
You are translating items from a survey as part of a cross-cultural psychological study. 
Translate the text below into the six target languages, returning *only* a valid
JSON object with the keys "IT", "PT-BR", "TR", "ES-ES", "SV", "NL".
– Preserve all HTML tags (e.g., bold) and Qualtrics piped-text (e.g. {{e://Field/var}}).  
– Keep sentence boundaries and placeholders unchanged.  
– The aim is psychological equivalence to allow comparing answers across languages.

TEXT:
\"\"\"{text}\"\"\"
"""

# ---------------------------------------------------------------------
# 1. Helpers
# ---------------------------------------------------------------------
def needs_translation(row: pd.Series)-> bool:
    """True if at least one target cell is empty/NaN."""
    return row[LANG_COLS].isna().any()

def existing_or_canned(src: str, tgt_lang: str) -> str | None:
    """
    Return a canned translation if available, otherwise None.
    Matching is case‑sensitive to avoid silent mistakes.
    """
    return CANNED.get(src, {}).get(tgt_lang)

def call_litellm(prompt: str) -> Dict[str, str]:
    """Robust call with simple exponential back‑off."""  
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = litellm.completion(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.0,
            )
            raw = response.choices[0].message.content.strip()
            # Allow the model to wrap JSON in markdown; strip it.
            json_str = re.search(r"\{.*\}", raw, flags=re.S).group(0)
            return json.loads(json_str)
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(2 ** attempt)          # back‑off
    return {}                                  # never reached

# ---------------------------------------------------------------------
# 2. Main routine
# ---------------------------------------------------------------------
def translate_workbook(infile: Path, outfile: Path) -> None:
    
    df = pd.read_excel(infile, sheet_name=SHEET_NAME)

    for idx, row in df.iterrows():
        src_text = row[SOURCE_COL]
        if pd.isna(src_text) or not needs_translation(row):
            continue                           # nothing to do

        # Fill from CANNED first ------------------------------------------------
        for lang in LANG_COLS:
            if pd.isna(row[lang]):
                canned = existing_or_canned(str(src_text).strip(), lang)
                if canned:
                    df.at[idx, lang] = canned

        # After canned pass, still missing anything?
        if not df.loc[idx, LANG_COLS].isna().any():
            continue                           # done, saved an API call

        # ---------------------------------------------------------------------
        # 3. LLM API request
        # ---------------------------------------------------------------------
        prompt = PROMPT_TEMPLATE.format(text=src_text)
        translations = call_litellm(prompt)

        # Update dataframe
        for lang in LANG_COLS:
            if pd.isna(df.at[idx, lang]):      # double‑check not overwritten
                df.at[idx, lang] = translations.get(lang, "")

        time.sleep(SLEEP_BETWEEN)              # throttle

    # -------------------------------------------------------------------------
    # 4. Save a new workbook (preserve original)
    # -------------------------------------------------------------------------
    df.to_excel(outfile, index=False)
    print(f"✓ Translation finished. Output saved to: {outfile.resolve()}")

# ---------------------------------------------------------------------
# 5. Entry‑point guard -------------------------------------------------
# ---------------------------------------------------------------------
if __name__ == "__main__":
    translate_workbook(INPUT_FILE, OUTPUT_FILE)




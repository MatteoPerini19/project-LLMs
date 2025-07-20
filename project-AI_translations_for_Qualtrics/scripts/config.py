"""
config.py
=========

Centralized configuration for the Qualtrics AI‑translation pipeline.

This module loads environment variables from a local ``.env`` file (if
present) and exposes **paths, model defaults, and batch‑size
constants** used across the project.

Nothing here should perform heavy logic; keep it declarative so that
importing this file never incurs side‑effects beyond reading the env.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# --------------------------------------------------------------------------- #
# Load .env early so that anything below can rely on `os.getenv()`.
# --------------------------------------------------------------------------- #
load_dotenv()

# --------------------------------------------------------------------------- #
# Project root & canonical directories
# --------------------------------------------------------------------------- #

# Path to: project-LLMs / project-AI_translations_for_Qualtrics
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Data folders
DATA_DIR: Path = PROJECT_ROOT / "data"
INPUT_DIR: Path = DATA_DIR / "input"
CACHE_PATH: Path = DATA_DIR / "tmp_cache.jsonl"
CANNED_DICT_PATH: Path = DATA_DIR / "canned_translations.json"

# Output folders
OUTPUT_DIR: Path = PROJECT_ROOT / "outputs" / "translated_csv"
LOG_DIR: Path = PROJECT_ROOT / "outputs" / "logs"
REPORT_DIR: Path = PROJECT_ROOT / "outputs" / "reports"

# Prompt template
PROMPT_TEMPLATE_PATH: Path = PROJECT_ROOT / "prompt_AI_translation_instructions.txt"

# --------------------------------------------------------------------------- #
# LLM & batching parameters
# --------------------------------------------------------------------------- #

# Default model name; overridable via CLI or env var
MODEL_NAME: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# Default items per single LLM prompt; can be tuned via CLI or env var
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))

# Timeout (seconds) for each LiteLLM request
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))

# Deterministic output: 0 = fully greedy
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0"))

# Maximum retry attempts for a single LiteLLM request
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "4"))

# Default set of target languages used when --langs is omitted
DEFAULT_LANGS: list[str] = ["it", "pt-br", "tr", "es-es", "sv", "nl"]

# --------------------------------------------------------------------------- #
# Exportable names
# --------------------------------------------------------------------------- #
__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "INPUT_DIR",
    "CACHE_PATH",
    "CANNED_DICT_PATH",
    "OUTPUT_DIR",
    "LOG_DIR",
    "REPORT_DIR",
    "PROMPT_TEMPLATE_PATH",
    "MODEL_NAME",
    "BATCH_SIZE",
    "LLM_TIMEOUT",
    "TEMPERATURE",
    "MAX_RETRIES",
    "DEFAULT_LANGS",
]
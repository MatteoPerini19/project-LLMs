"""
test.py
Quick check that call_llm() works with real API call using a mock prompt.
Run: python -m project-AI_translations_for_Qualtrics.scripts.test
"""

import sys
from pathlib import Path

# Ensure we can import sibling scripts
HERE = Path(__file__).parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from litellm_client import call_llm  # type: ignore
import config

# Enable debug prints
config.PRINT_FIRST_PROMPT = True
config.PRINT_FIRST_RESPONSE = True

FAKE_PROMPT = 'Return {"hi":"there"} ONLY. No extra text.'

if __name__ == "__main__":
    result = call_llm(
        prompt=FAKE_PROMPT,
        model=None,
        language="IT",
        timeout=30,
        max_retries=1,
        temperature=0
    )
    print("LLM said:", result)
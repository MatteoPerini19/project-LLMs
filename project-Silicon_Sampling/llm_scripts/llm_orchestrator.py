"""
llm_orchestrator.py
───────────────────
1. Fill output_memory_1.jsonl to N lines.
2. Patch template_siliconsampling.py to suffix "_2" and fill output_memory_2.jsonl to N lines.
3. Launch template_analysis.py once *both* files are ready, then reset SUFFIX back to "_1".

Uses only the Python standard library.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
N_LINES_TARGET = 101        # desired number of rows in output_memory_1.jsonl

ROOT_DIR   = Path(__file__).resolve().parents[2]        # …/project-LLMs
SCRIPTS_DIR = ROOT_DIR / "project-Silicon_Sampling" / "llm_scripts"
OUTPUT_DIR = ROOT_DIR / "project-Silicon_Sampling" / "llm_outputs"

OUTPUT1 = OUTPUT_DIR / "output_memory_1.jsonl"
OUTPUT2 = OUTPUT_DIR / "output_memory_2.jsonl"

TEMPLATE_SIL = SCRIPTS_DIR / "template_siliconsampling.py"
TEMPLATE_AN  = SCRIPTS_DIR / "template_analysis.py"

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def count_lines(path: Path) -> int:
    """Return number of non‑blank lines; 0 if file is missing."""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())

def truncate(path: Path, max_lines: int) -> None:
    """Keep only the first *max_lines* lines of *path*."""
    with path.open(encoding="utf-8") as f:
        first = [line for _, line in zip(range(max_lines), f)]
    with path.open("w", encoding="utf-8") as f:
        f.writelines(first)

def run(script: Path) -> None:
    """Run a Python script in a blocking subprocess."""
    subprocess.run([sys.executable, str(script)], check=True)

def set_suffix(target: str) -> None:
    """
    Patch template_siliconsampling.py so that
    the line starting with `SUFFIX =` equals the given target
    (e.g. "_1" or "_2").
    """
    assert target in ("_1", "_2"), "target suffix must be '_1' or '_2'"
    text = TEMPLATE_SIL.read_text(encoding="utf-8")
    new_text, changed = [], False
    for line in text.splitlines(keepends=True):
        if line.strip().startswith("SUFFIX"):
            if target not in line:
                # replace whatever comes after '=' with the target suffix
                new_text.append('SUFFIX = "' + target + '"          # managed by llm_orchestrator.py\n')
                changed = True
            else:
                new_text.append(line)
                changed = True
        else:
            new_text.append(line)
    if not changed:
        raise RuntimeError("Could not locate SUFFIX declaration in template_siliconsampling.py")
    TEMPLATE_SIL.write_text("".join(new_text), encoding="utf-8")
    print(f"📝 Patched template_siliconsampling.py → SUFFIX='{target}'")

def ensure_n_lines(output_path: Path, suffix: str) -> None:
    """
    Make repeated calls to template_siliconsampling.py (with the specified suffix already set)
    until *output_path* contains exactly N_LINES_TARGET non‑blank lines.
    """
    lines = count_lines(output_path)
    if lines > N_LINES_TARGET:
        prev = lines
        truncate(output_path, N_LINES_TARGET)
        lines = N_LINES_TARGET
        print(f"✂️ Trimmed {output_path.name} from {prev} to {N_LINES_TARGET} lines.", flush=True)
    while lines < N_LINES_TARGET:
        print(f"➕ {lines}/{N_LINES_TARGET} lines [{suffix}] — running silicon sampling.")
        run(TEMPLATE_SIL)
        lines = count_lines(output_path)
        if lines > N_LINES_TARGET:
            prev = lines
            truncate(output_path, N_LINES_TARGET)
            lines = N_LINES_TARGET
            print(f"✂️ Trimmed {output_path.name} from {prev} to {N_LINES_TARGET} lines.", flush=True)
    print(f"✅ Target reached for {output_path.name} ({N_LINES_TARGET} lines).")

# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Phase 1: ensure _1 dataset
    set_suffix("_1")
    ensure_n_lines(OUTPUT1, "_1")

    # Phase 2: ensure _2 dataset
    set_suffix("_2")
    ensure_n_lines(OUTPUT2, "_2")

    # Both datasets ready → run analysis
    print("📊  Both datasets complete — launching template_analysis.py …")
    run(TEMPLATE_AN)

    # Restore SUFFIX to _1 for next cycle
    set_suffix("_1")
    print("🎉 Pipeline complete and reset.")

if __name__ == "__main__":
    main()

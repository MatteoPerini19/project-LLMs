# Silicon Sampling — Project Overview

**Overview.** This repository demonstrates *silicon sampling*: recruiting large language models (LLMs) as high‑throughput, low‑cost “silicon participants” whose aggregated responses approximate the distributions obtained from human subjects.  

The included Python scripts cover three stages:

1. **Sampling** – `template_siliconsampling.py` sends batched, asynchronous API calls and logs each completion to a JSONL file.  
2. **Orchestration** – `llm_orchestrator.py` cycles the sampling script until each experimental condition reaches a predefined sample size, then triggers the statistical analysis.  
3. **Analysis** – `template_analysis.py` (single‑item payloads) and `template_analysis_multipleitems.py` (multi‑item payloads) compute descriptive statistics, Welch *t*, Bayes Factors, and effect sizes from the resulting logs.

Use this scaffold for any between‑condition design in which the outcome can be inferred from free‑text completions.

---

# Silicon‑Sampling Quick‑Start Guide


---


## 0. Prerequisites and Folder Layout

Create (or verify) the following directory tree inside your project root:

```
project-LLMs/
├── .env                                    # **NOT** committed; stores your API keys
├── .gitignore                              # must include `.env`
├── requirements.txt                        # bash: pip install -r requirements.txt
└── project-Silicon_Sampling/
    ├── README_silicon_sampling.md
    ├── llm_prompts/                        #  prompt text files
    │   ├── prompt_1.txt
    │   └── prompt_2.txt
    ├── llm_outputs/                        # JSONL logs grow here
    │   ├── output_memory_1.jsonl
    │   └── output_memory_2.jsonl
    └── llm_scripts/                        # Python scripts
        ├── functions_parallel_calls.py
        ├── template_siliconsampling.py
        ├── template_analysis.py
        ├── template_analysis_multipleitems.py
        └── llm_orchestrator.py
```

### Customizable Parameters

| Script | Variable | Description |
|--------|----------|-------------|
| `template_siliconsampling.py` | `MODEL` | LLM endpoint (e.g., `"gemini/gemini-2.5-flash"`). |
| | `NUM_CALLS` | Completions per batch. |
| | `CONCURRENCY` | Concurrent API calls (higher is faster but may generate errors). |
| `template_analysis.py` | `KEY_NAME` | JSON key to analyse (single‑item payloads). |
| | `CONDITION_A_NAME`, `CONDITION_B_NAME` | Labels for the two conditions. |
| | `PRINT_RAW_VALUES`, `WRITE_CSV` | Verbose output and raw CSV export. |
| `llm_orchestrator.py` | `N_LINES_TARGET` | Target observations per condition before analysis triggers. |
| `template_analysis_multipleitems.py` | `ITEM_KEYS` | List of item keys to average per response. |
| | `REVERSED_KEYS` | Subset of items to reverse‑score. |
| | `LIKERT_MIN`, `LIKERT_MAX` | Scale endpoints used for reverse‑scoring. |
| | `PRINT_RAW_VALUES`, `WRITE_CSV` | Same diagnostics options as above. |

* Place your LLM provider credentials in **`.env`**, e.g.  
  `OPENAI_API_KEY="sk-..."`  
  Any additional keys (e.g. Azure, Anthropic) go here as well.
* Ensure `.gitignore` lists `.env` so that secret keys never reach the repository.
* All important knobs—file paths, model, batch size, etc.—sit in the **Configuration** block at the top of each script. Adjust them there; no need to hunt through the code.

---

## 1. Prepare Your Two Prompts

* **Control** – baseline condition: `project-Silicon_Sampling/llm_prompts/prompt_1.txt`
* **Treatment** – experimental condition: `project-Silicon_Sampling/llm_prompts/prompt_2.txt`

Keep the prompts identical except for the manipulation you wish to test. 

---

## 2. Configure `template_siliconsampling.py`

Open the script and inspect the **Configuration** block:

```python
PROMPT_PATH  = Path("project-Silicon_Sampling/llm_prompts/prompt_1.txt")   # choose the prompt file
OUTPUT_PATH  = Path("project-Silicon_Sampling/llm_outputs/output_memory_1.jsonl")  # choose an output file
MODEL        = "openai/gpt-4o"
NUM_CALLS    = 25     # parallel completions per run
CONCURRENCY  = 15     # in‑flight requests
MAX_TOKENS   = None   # leave None for model default
```

* Point `PROMPT_PATH` at your current prompt (Control or Treatment).
* Point `OUTPUT_PATH` at a unique JSONL file, e.g. `output_control.jsonl` or `output_treatment.jsonl`.
* Adjust `NUM_CALLS` to the batch size you want for each run. Note: too many simultaneous calls can lead to errors. 

---

## 3. Automated Sampling and Analysis with the Orchestrator

The file `llm_scripts/llm_orchestrator.py` automates the entire sampling‑analysis cycle.

```python
# Inside llm_orchestrator.py
N_LINES_TARGET = 300      # rows per condition (change as needed)
```

Executing the orchestrator performs the following steps:

1. **Fill** `output_memory_1.jsonl` until it reaches *N* lines (truncating any excess).  
2. **Patch** `template_siliconsampling.py` so that it switches to suffix “_2” and subsequently fill `output_memory_2.jsonl` to *N* lines.  
3. **Launch** `template_analysis.py` once **both** files are ready.  
4. Reset `template_siliconsampling.py` back to suffix “_1” so that subsequent runs start from the first condition.

```bash
cd project-Silicon_Sampling/llm_scripts
python llm_orchestrator.py
```


---

## 4. Manual Sampling (Optional)

For manual operation,  
run `template_siliconsampling.py` directly, set the `SUFFIX` variable yourself, and monitor the JSONL lengths before running the analysis.

---

## 5. Multiple‑Item Analysis

If your prompts ask LLMs to return **several numeric items** (e.g., `{"item1": 9, "item2": 4, "item3": 8}`), use `template_analysis_multipleitems.py` (or write it in the orchestrator). 

```python
ITEM_KEYS     = ["item1", "item2", "item3"]   # items to average
REVERSED_KEYS = ["item2"]                     # items to reverse‑score
LIKERT_MIN    = 1
LIKERT_MAX    = 7
```

The script:

* reverse‑scores the specified items,  
* computes the mean per response,  
* outputs descriptive stats, Welch *t*, Bayes Factor, Cohen’s *d* with 95 % / 99 % CIs,  
* saves a histogram, and optionally writes a CSV.

Run it after the orchestrator (or manual runs) have produced the JSONL files:

```bash
python project-Silicon_Sampling/llm_scripts/template_analysis_multipleitems.py
```

---

## 6. Iterate, Refine, Conquer

1. Tweak the prompts for sharper manipulations or for increasing generalizability.
2. Rerun silicon sampling, the JSONL grows; nothing is overwritten.  
3. Rerun the analysis when you reach your target sample size.  

> **Nota bene:** If you change the prompts, consider starting with fresh JSONL files and saving the old ones with a different names. 


# Silicon‑Sampling Quick‑Start Guide


---


## 0. Prerequisites and Folder Layout

Create (or verify) the following directory tree inside your project root:

```
py_LLM_translations/
├── .env                      # **NOT** committed; stores your API keys
├── .gitignore                # must include `.env`
├── .requirements.txt         # bash: pip install -r requirements.txt
├── llm_prompts/              # prompt text files
│   ├── prompt_1.txt
│   └── prompt_2.txt
├── llm_outputs/              # JSONL logs grow here
│   ├── output_memory_1.jsonl
│   └── output_memory_2.jsonl
└── llm_scripts/              # Python scripts
    ├── template_siliconsampling.py
    └── template_analysis.py
```

* Place your OpenAI (or other provider) credentials in **`.env`**, e.g.  
  `OPENAI_API_KEY="sk-..."`  
  Any additional keys (e.g. Azure, Anthropic) go here as well.
* Ensure `.gitignore` lists `.env` so that secrets never reach the repository.
* All important knobs—file paths, model, batch size, etc.—sit in the **Configuration** block at the top of each script. Adjust them there; no need to hunt through the code.

---

## 1. Prepare Your Two Prompts

* **Control** – baseline condition: `llm_prompts/prompt_1.txt`
* **Treatment** – experimental condition: `llm_prompts/prompt_2.txt`

Keep the prompts identical except for the manipulation you wish to test. 

---

## 2. Configure `template_siliconsampling.py`

Open the script and inspect the **Configuration** block:

```python
PROMPT_PATH  = Path("llm_prompts/prompt_1.txt")   # choose the prompt file
OUTPUT_PATH  = Path("llm_outputs/output_memory_1.jsonl")  # choose an output file
MODEL        = "openai/gpt-4o"
NUM_CALLS    = 25     # parallel completions per run
CONCURRENCY  = 15     # in‑flight requests
MAX_TOKENS   = None   # leave None for model default
```

* Point `PROMPT_PATH` at your current prompt (Control or Treatment).
* Point `OUTPUT_PATH` at a unique JSONL file, e.g. `output_control.jsonl` or `output_treatment.jsonl`.
* Adjust `NUM_CALLS` to the batch size you want for each run. Note: too many simultaneous calls can lead to errors. 

---

## 3. Fire the Script Repeatedly

From your virtual‑env shell run:

```bash
python llm_scripts/template_siliconsampling.py
```

Each run appends **NUM_CALLS** new records to the JSONL and prints the cumulative count. Launch the script again and again until the file shows the desired number of observations.

---

## 4. (Optional) Inspect the Raw File

Open the JSONL and check a few lines. You should see clean JSON objects such as:

```json
{"timestamp": "...", "response_json": {"depth": 8, "topic": "..."}, ...}
```

Make sure "response_json" has a valid json object as value.


---

## 5. Run the Analysis

Edit `template_analysis.py` in the **Configuration** block:

```python
FILE_A = Path("llm_outputs/output_control.jsonl")
FILE_B = Path("llm_outputs/output_treatment.jsonl")
CONDITION_A_NAME = "Control"
CONDITION_B_NAME = "Treatment"
```

Then run:

```bash
python llm_scripts/template_analysis.py
```

The script will print descriptive statistics, a Welch *t*‑test with two‑tailed *p*, a BIC‑based Bayes Factor, and save:

* A bar chart of integer‑rounded scores → `analysis_depth_distributions.png`
* A CSV with raw values → `analysis_depth_values.csv`

---

## 6. Iterate, Refine, Conquer

1. Tweak the prompts for sharper manipulations.  
2. Rerun silicon sampling — the JSONL grows; nothing is overwritten.  
3. Rerun the analysis when you reach your target sample size.  

> **Nota bene:** If you change prompt wording mid‑experiment, start a fresh JSONL.


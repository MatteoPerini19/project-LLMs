import litellm as llm
llm.set_verbose = False         # suppress repetitive “Give Feedback / Get Help”
import os
from dotenv import load_dotenv
import json, textwrap
import math
import datetime
import re
from typing import Any

from rich import print as rprint
from rich.pretty import Pretty

# ---------- Helper: sanitize and isolate JSON payload ---------- #
def _extract_json_payload(text: str) -> str:
    """
    Return the substring containing the JSON object, stripped of Markdown
    code fences, leading/trailing noise, and normalized to straight quotes.
    """
    text = text.strip()

    # Remove ```json ... ``` fences
    if text.startswith("```"):
        m = re.match(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()

    # Keep only from the first '{' to the last '}'
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    # Normalise curly quotes → straight quotes
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return text



load_dotenv()  # loads variables from .env 


# COMANDI DA RICORDARE: 
## - response.model_dump()   # converte in un dizionario Python 

# IMPARA 
## Parallel prompting: richiedi n=5, mantieni gli ID, approva offline la variante migliore.

	# 11.	Dynamic temperature
	# •	Se il gap fra top-logprob è piccolo, abbassi temperature per risposte più stabili, e viceversa.

	# 13.	Self-consistency decoding
	# •	Genera N risposte, fai votare un critico LLM o prendi la moda—precisione ↑ senza retrain.


# STRATEGY SILICON SAMPLING
# Prendi il codice "ASYNC BATCH - MULTIPLE CALLS" e crea una versione per due tipi diversi di prompt e due tipi diversi di output. 
# Imposta il sample size ("num_calls"). 
# Esegui. 





################################################
#################### PROMPT ####################
################################################

 # Load prompt from external file (e.g., prompt.txt)
with open("llm_prompts/prompt_1.txt", "r", encoding="utf-8") as _pf:
    prompt = _pf.read().strip()

message = [{
    "content": prompt,
    "role": "user"
}]

##################################################
#################### CALL LLM ####################
##################################################


response = llm.completion(
  model="openai/gpt-4o",
  messages=message, 
  # logprobs=True,         # request log‑probs data
  # top_logprobs=5,        # how many alternatives per token
  # stream=True,   # stampa flusso di parole
)


##########################################################
#################### PRINTING OPTIONS ####################
##########################################################

### Estrarre solo ciò che conta
print("🔴🔴🔴")
print(f"Prompt: \n{prompt}")

print("🔴🔴🔴")
msg  = response.choices[0].message.content
cost = response.usage.total_tokens
print(f"🔹 Output:\n{msg}\n\n🔹 Tokens: {cost}")
print("🔴🔴🔴")


### Print logprobs 
# print("🔴🔴🔴")
# lp = response.choices[0].logprobs
# first_lp = lp.content[0]                          # first token's log‑prob object
# prob_first = math.exp(first_lp.logprob)           # convert log‑prob → probability
# fourth_lp = lp.content[3] 
# prob_fourth = math.exp(fourth_lp.logprob)
# print(f"🔹 Confidence first token: {prob_first:.4f}\n")
# print(f"🔹 Confidence fourth token: {prob_fourth:.4f}\n")
# rprint(Pretty(lp, max_depth=10, indent_guides=True))
# print("🔴🔴🔴")


### Libreria rich (colori e collapsible)
# print("🔴🔴🔴")
# rprint(Pretty(response.model_dump(), max_depth=10, indent_guides=True))
# print("🔴🔴🔴")

### Estrai tutto, brutalmente 
# print("🔴🔴🔴")
# print(response)
# print("🔴🔴🔴")

### pprint (Pretty Printer standard)
# print("🔴🔴🔴")
# from pprint import pprint
# pprint(response.model_dump(), depth=3, compact=False)
# print("🔴🔴🔴")

### Struttura gerarchica con rientri; niente escape unicode
# print("🔴🔴🔴")
# r_dict = json.dumps(response.model_dump(), indent=2, ensure_ascii=False)
# print(r_dict)
# print("🔴🔴🔴")

### If stram=True
# print("🔴🔴🔴")
# for chunk in response:
#     # ogni chunk è un ModelResponse con .choices[0].delta.content
#     delta = chunk.choices[0].delta.content or ""
#     print(delta, end="", flush=True)
# print()  # newline finale
# print("🔴🔴🔴")


#######################################################
#################### OUTPUT MEMORY ####################
#######################################################

### Save output in llm_outputs/output_memory_1.jsonl
try:
    clean_msg = _extract_json_payload(msg)

    # ── Attempt JSON parse; fall back to raw text ──
    try:
        parsed_response = json.loads(clean_msg)
    except json.JSONDecodeError:
        parsed_response = clean_msg

    record = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "response_json": parsed_response,   # dict/list if JSON, else str
        "response_raw": msg,                # always the verbatim text
        "prompt": prompt,
        "model": response.model,
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }
    with open("llm_outputs/output_memory_1.jsonl", "a", encoding="utf-8") as fout:
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")
except Exception as log_err:
    print(f"⚠️ Impossibile salvare in llm_outputs/output_memory: {log_err}")


### Ottieni scores dal file jsonl
import json, pathlib, statistics

# ---------- Helper: safe stdev ----------
def _safe_stdev(seq: list[float]) -> float:
    """Return stdev(seq) if len(seq) ≥ 2, else NaN."""
    return statistics.stdev(seq) if len(seq) >= 2 else float("nan")
scores = []
path = pathlib.Path("llm_outputs/output_memory_1.jsonl")      # path to the JSONL file
with path.open(encoding="utf-8") as f:
    # Alcune righe potrebbero avere due record concatenati senza newline.
    decoder = json.JSONDecoder()
    buffer = ""
    for chunk in f:
        buffer += chunk
        idx = 0
        while idx < len(buffer):
            try:
                obj, end = decoder.raw_decode(buffer, idx)
                idx = end            # advance cursor
                # --- Process the decoded object ---
                raw = obj["response_json"]

                # If already a dict/list, keep it; if str, try to parse as JSON
                if isinstance(raw, str):
                    clean_raw = _extract_json_payload(raw)
                    try:
                        inner = json.loads(clean_raw)
                    except json.JSONDecodeError:
                        continue    # skip non‑JSON
                else:
                    inner = raw

                # Accumula il primo e secondo valore, qualunque sia il nome delle chiavi
                if isinstance(inner, dict) and "score" in inner:
                    scores.append(inner["score"])

            except json.JSONDecodeError:
                # Non abbiamo ancora un JSON completo; continua a leggere
                break
        # Remove processed part of buffer
        buffer = buffer[idx:]
mean_rating = statistics.mean(scores)
print(f"🔸 Media punteggi: {mean_rating:.2f}")
print("🔴🔴🔴")



#########################################################
#################### WRAPPE FUNCTION ####################
#########################################################


# def ask_llm(prompt: str,
#             model: str = "openai/gpt-4o",
#             max_tokens: int = 512,
#             logprobs: bool = False,
#             top_logprobs: int = 5,
#             stream: bool = False,
#             **kwargs):
#     """One-liner convenience wrapper around llm.completion()."""
#     messages = [{"role": "user", "content": prompt}]
#     return llm.completion(
#         model=model,
#         messages=messages,
#         max_tokens=max_tokens,
#         logprobs=logprobs,
#         top_logprobs=top_logprobs,
#         stream=stream,
#         **kwargs
#     )

# ask_llm("Che ore sono a Roma?")




##########################################################
#################### TRY - EXCEPT ####################
##########################################################

# ###Retry & back-off
# for attempt in range(3):
#     try:
#         response = ask_llm(prompt, model=model, **kwargs)
#         break
#     except OpenAIError as err:
#         time.sleep(2**attempt)
# else:
#     raise RuntimeError("⚠️⚠️⚠️ LLM failed after 3 attempts ⚠️⚠️⚠️")


# ### Provider fallback
# try:
#     response = llm.completion(
#         model="openai/gpt-4o",
#         messages=message,
#         max_tokens=512
#     )
# except OpenAIError as err:
#     print(f"⚠️⚠️⚠️ Provider failure: {err} ⚠️⚠️⚠️")
#     response = llm.completion(
#         model="google/gemini-2.5-flash",
#         messages=message,
#         max_tokens=512
#     )


############################################################
#################### NOTEBOOK HELPER #######################
############################################################

# from rich.pretty import Pretty as _Pretty
# from rich import print as _rprint
# from IPython.display import display as _display, Markdown as _md
# from tqdm.notebook import tqdm as _tqdm

# def nb_pretty(obj, depth: int = 4):
#     """Rich-pretty print any Python object inside a notebook cell."""
#     _rprint(_Pretty(obj, max_depth=depth, indent_guides=True))

# def nb_cost_report(response_obj, price_dict: dict):
#     """
#     Display a small cost report for a ModelResponse in a notebook.

#     Parameters
#     ----------
#     response_obj : litellm.ModelResponse
#         The response returned by llm.completion().
#     price_dict : dict
#         Mapping {"provider/model": (prompt_price, completion_price)} in $/1K tokens.
#     """
#     u = response_obj.usage
#     model_name = response_obj.model
#     p_prompt, p_comp = price_dict.get(model_name, (0.0, 0.0))
#     cost = u.prompt_tokens * p_prompt + u.completion_tokens * p_comp
#     _display(_md(f"**Cost estimate** for `{model_name}`  \n"
#                  f"Prompt tokens: `{u.prompt_tokens}`  \n"
#                  f"Completion tokens: `{u.completion_tokens}`  \n"
#                  f"**Total cost:** `${cost:.4f}`"))

# def nb_stream(response_stream):
#     """
#     Stream chunks in a notebook with a live Markdown cell _and_ a tqdm progress bar.
#     Note: the bar is indeterminate (no total), increments by 1 per chunk.
#     """
#     buffer = []
#     with _tqdm(unit="tok", desc="Streaming", leave=False) as bar:
#         for chunk in response_stream:
#             delta = chunk.choices[0].delta.content or ""
#             buffer.append(delta)
#             _display(_md("".join(buffer)), clear=True)
#             bar.update(1)



####################################################################
################### ASYNC BATCH - MULTIPLE CALLS ###################
####################################################################

"""
Async I/O template for LiteLLM  
‒ Launch many requests concurrently with asyncio  
‒ Optional retry/back‑off via `tenacity`  
‒ Concurrency cap via `asyncio.Semaphore`  
"""

import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

# ---------- Generic async completion wrapper ---------- #

_concurrency_default = 10  # fallback if user doesn't pass a custom limit


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def _one_call(messages: list,
                    model: str,
                    max_tokens: int | None = None,
                    _sem: asyncio.Semaphore | None = None):
    """Single async call to LiteLLM guarded by an optional semaphore."""
    sem_ctx = _sem or asyncio.dummy_context()  # fallback context manager
    async with sem_ctx:
        kwargs = dict(model=model, messages=messages)
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        resp = await llm.acompletion(**kwargs)
    return resp


async def _batch_runner(
    num_calls: int,
    messages: list,
    model: str,
    max_tokens: int | None,
    concurrency: int,
):
    """Run *num_calls* in parallel and return list of ModelResponse objects."""
    sem = asyncio.Semaphore(concurrency)
    tasks = [
        asyncio.create_task(_one_call(messages, model, max_tokens, sem))
        for _ in range(num_calls)
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)


### Main function to use for multiple parallel calls 
def asynch_completion(
    *,
    num_calls: int,
    messages: list,
    model: str = "openai/gpt-4o",
    max_tokens: int | None = None,
    concurrency: int | None = None,
):
    """
    Fire num_calls asynchronous completions in parallel.

    Parameters
    ----------
    num_calls : int        Number of parallel requests to send.
    messages  : list       Chat messages list (same as llm.completion).
    model     : str        Provider/model identifier.
    max_tokens: int | None Optional token cap.
    concurrency: int | None Limit of simultaneous in-flight requests.
                            Defaults to _concurrency_default.
    Returns
    -------
    List[litellm.ModelResponse] or Exception objects (if any call failed).
    """
    conc = concurrency or _concurrency_default
    return asyncio.run(
        _batch_runner(num_calls, messages, model, max_tokens, conc)
    )

# ---------- End generic async wrapper ---------- #



### 🟣🟣🟣 Template parallel llm calls 🟣🟣🟣

with open("llm_prompts/prompt_1.txt", "r", encoding="utf-8") as _pf:
    prompt = _pf.read().strip()


message = [{"role": "user", "content": prompt}]

results = asynch_completion(
    num_calls=5,                    # select number of calls (problems with >=200) 
    messages=message,
    model="openai/gpt-4o",
    concurrency=15,                   # number of simultaneous calls
)



### Save results

for res in results:
    # Se la coroutine ha lanciato un'eccezione, logga e passa oltre
    if isinstance(res, Exception):
        print("❌", res)
        continue

    out_text = res.choices[0].message.content.strip()
    print("🔹 Output:", out_text)

    # ── Salva il risultato nel file JSONL (stile uniforme) ──
    try:
        clean_out = _extract_json_payload(out_text)

        # ── Attempt JSON parse; fall back to raw text ──
        try:
            parsed_out = json.loads(clean_out)
        except json.JSONDecodeError:
            parsed_out = clean_out

        rec = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
            "response_json": parsed_out,
            "response_raw": out_text,
            "prompt": prompt,
            "model": res.model,
            "prompt_tokens": res.usage.prompt_tokens,
            "completion_tokens": res.usage.completion_tokens,
            "total_tokens": res.usage.total_tokens
        }
        with open("llm_outputs/output_memory_1.jsonl", "a", encoding="utf-8") as fout:
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as log_err:
        print(f"⚠️ Impossibile salvare in llm_outputs/output_memory: {log_err}")
print("🔴🔴🔴")



### Compute mean 

# Estrazione valori da jsonl
"""
read_depths.py  –  Estrae tutti i valori in slot #1 da llm_outputs/output_memory_1.jsonl.

Assume che:
• Ogni riga del file sia un JSON valido.
• Il campo "response_json" contenga un dict o una lista
  con almeno un valore numerico (e.g. {"depth": 8, ...}).
"""

import json
from pathlib import Path

FILE = Path("llm_outputs/output_memory_1.jsonl")

slot1_values: list[float] = []

with FILE.open(encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue  # salta righe vuote
        obj = json.loads(line)          # record completo
        payload = obj.get("response_json")

        # --- estrai il primo valore numerico ---
        if isinstance(payload, dict):
            # l'ordine d'inserimento delle chiavi è preservato (Python ≥3.7)
            iterator = payload.values()
        elif isinstance(payload, list):
            iterator = payload
        else:
            continue  # formati imprevisti

        for v in iterator:
            if isinstance(v, (int, float)):
                slot1_values.append(v)
                break  # passa al prossimo record

print(f"Totale record letti: {len(slot1_values)}")
print("Esempio primi 10 valori:", slot1_values[:10])

# ---- Sintesi statistica dello slot #1 ----
import statistics
n = len(slot1_values)
mean1 = statistics.mean(slot1_values) if slot1_values else float("nan")
sd1 = statistics.stdev(slot1_values) if len(slot1_values) >= 2 else float("nan")

print(f"🔸 Mean (slot #1): {mean1:.2f}")
print(f"🔸 SD   (slot #1): {sd1:.2f}")
print(f"🔸 N    (slot #1): {n}")
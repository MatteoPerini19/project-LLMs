# GOALS

- Take a Qualtrics translation file.

- Apply "canned" traslations, that should stay consistent across the survey and are predetermined by the user.
    - Also items which just images will be "translated" by python without llms (e.g., <img height="500" src="https://psychru.qualtrics.com/CP/Graphic.php?IM=IM_IqEpn11a0rNKolv" style="width: 493px; height: 500px;" width="493" />)

- *Respect* the fact that some translations are already filled by the user. DON'T overwrite them. 

- Call LLMs for the remaining translations. 
    - Best approach would be to batch several items together in a single call (let's say: 10 items per call), so the model also has additional contextual awareness, and keep the languages separate (risk of cognitive cross-talk)

- *Take into account* that some items might repeat across the survey. If they repeat, make sure the translation is the same. If they are identical in English, you want them to be identical also in the translated languages. 
    - Note: a problem might arise for items that are QUASI-IDENTICAL... ***how should we handle these?***
    - Partial solution: set model temperature to zero (OpenAI models default to temperature≈0.7)

- *Give some common sense* specific to this goal to the model, important when translating ambiguous and isolated items (e.g., "Prolific" understood as a synonym for "fertile"). 
    - For this reason, it's important to double check.
    - Depending on the token budget and LLM's capabilities, consider feeding the model, every time you call it, also with (1) the preregistration of your study and (2) the full quationnaire to let it have maximal contextual awareness. Another option is to ask an LLM to write a detailed but compressed summary of the questionnaire / study (~1k tokens), to feed each time with the translation instructions. However, this could leed to attention dilution. 
    - Asking the model to translate multiple subsequent items simultaneously provide it with some context of the translation.

- Note: Treat ~60% of the formal token limit as your working budget to prevent loss of quality. Keep the most relevant information at the beginning or at the end of a prompt. 


- Cache across calls: Our translation_memory.py prevents repeat work; no need to resend identical chunks.



## Running the Translation Pipeline

You have **two ways** to launch the project:

### 1. Command-line
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

### 2. VS Code one-click

1.	Open scripts/orchestrator.py.
2.	Ensure .venv is the selected interpreter.
3.	Press ▶ Run Python File.

(Add CLI flags like --langs de,fr in the Run & Debug panel if desired.)

⸻

Tweaking defaults (edit scripts/config.py or set env vars)

Constant	        Purpose
MODEL_NAME	        LLM model (e.g., gpt-4o-mini)
BATCH_SIZE	        Items per LLM call (default 10)
LLM_TIMEOUT	        Seconds before a request times out
TEMPERATURE	        0 = deterministic, >0 adds randomness
MAX_RETRIES	        Retry attempts on 429/5xx (default 4)
DEFAULT_LANGS	    Languages used when --langs is omitted
Path constants	    Change folder layout if you must

All constants can also be overridden via environment variables, e.g.:
export BATCH_SIZE=20
export MODEL_NAME=gemini/gemini-2.5-pro

Outputs land under project-AI_translations_for_Qualtrics/outputs/. 



# DIRECTORY TREE 

project-LLMs/
├── .venv                                           # project virtual environment
├── .env                                            # chiavi API (git-ignored)
├── .gitignore                                      # include .env, *.jsonl, __pycache__/, ...
├── requirements.txt                                # pip3 install -r requirements.txt
└── project-AI_translations_for_Qualtrics/          # subproject root
    ├── README_AI_translations.md                   # project overview & goals
    ├── prompt_AI_translation_instructions.txt      # prompt for the translations, add the relevant instructions
    ├── data/
    │   ├── input/
    │   │   └── Qualtrics_translations.csv          # translation file downloaded from qualtrics
    │   ├── canned_translations.json                # multilingual dictionary set by the user
    │   └── tmp_cache.jsonl                         # incremental translation memory
    ├── outputs/
    │   ├── translated_csv/
    │   │   └── Qualtrics_translations_filled.csv   # fully populated survey
    │   ├── logs/
    │   │   └── litellm_calls_YYYY-MM-DD.jsonl      # per‑call LiteLLM log
    │   └── reports/
    │       └── ambiguous_items.xlsx                # near-duplicate audit, to manually review for homogeneity 
    └── scripts/
        ├── config.py                               # environment & constants
        ├── canned_loader.py                        # load canned dictionary
        ├── translation_memory.py                   # checks whether a given English string is already in the cache
        ├── litellm_client.py                       # wrapper around LiteLLM
        ├── orchestrator.py                         # CLI entry point
        ├── audit_fuzzy_matches.py                  # review near‑duplicates
        └── utils.py                                # shared helpers




# PROMPTS

- Add examples from the silicon sampling project to keep consistent style 

- Create similar branching structure (***think about this in advance***)

- ...



# SUMMARY OF PREREGISTRATION AND SURVEY


### Prompt for initial summary 

```
SYSTEM:
You are “Context-Summary Bot”, a meticulous methodological assistant.  
Your sole task is to digest two documents—(1) the preregistration of a cross-cultural psychological study, and (2) that study’s full Qualtrics questionnaire—and produce a concise but comprehensive summary (~1 000 tokens, ±20 %) that will be supplied to professional translators.

GUIDELINES:
1. Prioritize information that **impacts translation choices**, not statistical minutiae.  
2. Write in clear academic English (APA tone), no idioms or jokes.  
3. Output must be **plain text**, no markdown, no JSON, no code fences.  
4. Keep a logical hierarchy:
   • Study aim & theoretical background  
   • Participant population and recruitment platforms  
   • Survey structure (sections & item types)  
   • Critical wording nuances or culturally sensitive terms  
   • Glossary of study-specific terms (max 50 items)  
5. Omit personal data, IRB identifiers, or API keys.

```

### Summary (o3-pro + human)


```
===SUMMARY OF THE STUDY DESIGN AND THE SURVEY===

### Study aim 
The project meain goals are to examine how pathogen‑avoidance motivations, situational pathogen cues, and cultural pathogen prevalence jointly shape consumers’ attitudes toward, and willingness to pay (WTP) for, second‑hand clothing. 

### Participants
100-150 participants each from Canada, Netherlands, Sweden, Spain, Italy, Turkey, Brazil, Ghana, India. Eligibility: aged ≥ 18, resident of and born in one of the nine countries, currently at home (verified at start), fluent in one of seven survey languages. Recruitment via Prolific and BeSample. Platform ID field is mandatory and appears immediately after screening.

### Survey structure (ordered blocks and item types)
1. Introduction and screening (language selector; country list; “Are you at home?” yes/no).
2. Embedded‑data block (platform and participant ID).
3. Thank‑you preamble.
4. Multi‑page informed‑consent form (GDPR‑compliant; binary Yes/No choice).
5. Prime‑specific instructions (Pathogen prime or Cleanness prime) or none (Control).
6. ASHI picture‑rating tasks: nine clothing categories (t‑shirt, hat, socks, shoes, pants, backpack, sweater, blazer, coat); each category shows six second‑hand images followed by the Desirability/Pathogen‑salience slider set and a WTP slider.
7. PVD scale (timing depends on condition).
8. Second‑hand consumer‑behavior block (purchase frequency, behavioral intention, Net Promoter, attention check).
9. Motivation block: nine paired association and importance items plus “immaterial essence” valence question.
10. Personality and individual‑difference block (TIPI‑10, DPES‑Awe, political orientation, religiosity, paranormal belief scale, attention check).
11. Demographics (smell ability 0–10, age, gender, occupation, urbanicity, 10‑rung subjective‑status ladder).
12. End‑of‑survey message.&#x20;

### Critical wording nuances and culturally sensitive terms
• “Second‑hand” must be rendered unambiguously as previously‑owned apparel, not recycled textiles.
• Dermatological images are labeled only by clinical terms (“acne,” “psoriasis,” “warts”); translations must avoid stigmatizing slang.
• “Immaterial essence” examples (“energy,” “aura,” “karma,” “luck”) require culturally equivalent metaphysical concepts without religious offense.
• Political‑orientation anchors (“Extremely progressive,” “Extremely conservative”) should map onto local left‑right spectra.
• “Laundry detergent” refers to any product commonly used for washing clothes; translation must match household vernacular.
• The subjective‑status ladder metaphor (money, education, respect) should preserve the ladder visual and socioeconomic descriptors.

### Glossary of *Critical* Terms and Phrases as Intended in the Survey (keep in mind when choosing the best translation)
• "Appealing" – Aesthetic liking of the item’s look; **purely visual/subjective**, not functional quality.
• "Clean/hygienic" – Perceived absence of dirt, germs, or odors; preserve the **sanitary** nuance rather than “tidy.”
• "I would feel comfortable wearing it, even knowing someone else has worn it" – **Psychological ease** about using a used item, not physical comfort of fit or fabric.
• "I would like to have it, even knowing someone else has worn it" – Desire to **own/possess** the item, independent of price or purchase; avoid verbs meaning “borrow” or “wear.”
• Highest price you would be willing to pay (slider) – Measures the **maximum % of the new‑price** a respondent would pay; keep the *discount* concept explicit (0 = reject, 100 = pay full new price).
• Cleanliness/hygiene concerns – Worries about allergens, bacteria, viruses, insects; translate with both “clean” and “health” overtones.
• Sustainability – Environmental benefits (CO₂, waste reduction); avoid generic “durability” meanings.
• Economic convenience – **Cost‑saving** motive; choose wording for affordability/bargain, not “comfort” or “efficiency.”
• Quality concerns – Fear of **wear‑and‑tear defects**; stress material deterioration, not design preference.
• Emotional value – Positive **sentimental/treasure‑hunt joy**; avoid “emotional burden.”
• Fashion and uniqueness – Appeal of **distinctive/vintage style**; retain trendiness + individuality connotation.
• Social stigma – Negative **social judgment** or perceived lower status; include notions of peer criticism.
• Health risk – Potential for **infection, allergies, parasites**; be explicit about medical hazard (rather than mere preference for cleanness).
• Evaluate and order images from most to least disgusting – Instruction in pathogen priming; “disgusting” must convey **pathogen‑relevant revulsion**, not merely “ugly.”
• Drag‑and‑drop – UI action of moving pictures; choose interface term common in target language (e.g., “arrastra y suelta”).
• Laundry detergent – Standard household fabric‑washing product; avoid “dish soap” or “bleach” equivalents.
• Exact brand name / First ingredient – Require **verbatim text** from bottle; indicate that spelling must match label.
• Smell your detergent – Action cue; ensure verb implies **actively sniffing**.
• Imagining the scent – Instruction for those without detergent; preserve idea of **vivid mental simulation** of smell.
• How often do you buy (0–6 scale) – Frequency anchors must map to calendar terms (never → weekly or more often).
• Attention‑check item – Clearly label as a **trap question**; translation must preserve absurdity (“swim across the atlantic ocean”, not capitalized).
• Associate X with Y – Measures **mental linkage**, not causal belief; translate as “relate” or “connect,” not “cause.”
• Influence your decision – Degree to which factor **affects behavior**, not mere attitude.
• Extraverted, enthusiastic (TIPI item) – Keep trait pair; do not replace with unrelated synonyms.
• Select “Agree strongly” (embedded attention check) – Instruction must stand out; maintain imperative tone.
• Extremely progressive → Extremely conservative – Political spectrum; preserve *left–right* orientation familiar to target culture.
• Smelling ability (0–10 ladder) – Self‑rated olfactory acuity; anchors 0 = no smell, 10 = excellent.
• Subjective social‑status ladder – Visual metaphor of **rungs**; translation must instruct placing family on ladder representing money, education, respect.
This list covers every term the annotations flag as semantically delicate; adhere strictly to these definitions when producing localized versions.

===END OF SUMMARY===

```

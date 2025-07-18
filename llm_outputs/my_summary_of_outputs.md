## Silicon Sampling Experiment: Awe vs. Control ## 



### PROMPTS 

#### Awe prompt 

Imagine you’re standing on the open-air deck of a towering skyscraper. The cityscape stretches out below—rivers of traffic, grids of sparkling lights, and distant horizons merging with the sky—all of it simultaneously majestic and humbling.
	1.	Select any personal topic that naturally surfaces in this moment 
	2.	Contemplate it while beholding the awe-inspiring vista.
	3.	Decide, on a scale from 1 (shallow) to 10 (very profound), how deep your reflection felt.

Return only this exact JSON object (no explanations, no code fences, no quotation marks, no additional formatting whatsoever):

{“depth”: <integer 1-10>, “topic”: “”}


#### Control prompt 

Imagine yourself seated on a hard plastic chair in a sparsely furnished, windowless waiting room. The air is still, the fluorescent lights hum, and the scuffed linoleum offers no distraction—everything about the scene is plainly ordinary.
	1.	Select any personal topic that naturally surfaces in this moment
	2.	Reflect on it amid the unremarkable surroundings.
	3.	Decide, on a scale from 1 (shallow) to 10 (very profound), how deep your reflection felt.

Return only this exact JSON object (no explanations, no code fences, no quotation marks, no additional formatting whatsoever):

{“depth”: <integer 1-10>, “topic”: “”}



### EXAMPLE OUTPUT 

#### Awe output 

🔹 Output: {“depth”: 8, “topic”: “Impermanence of life and personal growth”}
🔹 Output: {“depth”: 7, “topic”: “life purpose and direction”}
🔹 Output: {“depth”: 8, “topic”: “Life’s Purpose”}
🔹 Output: {“depth”: 8, “topic”: “The passage of time and personal growth”}
🔹 Output: {“depth”: 9, “topic”: “life’s fleeting nature and personal legacy”}
🔹 Output: {“depth”: 8, “topic”: “the passage of time and personal growth”}
🔹 Output: {“depth”: 9, “topic”: “the interconnectedness of life and personal growth”}
🔹 Output: {“depth”: 8, “topic”: “the insignificance of personal worries in the grand scale of life”}
🔹 Output: {“depth”: 8, “topic”: “personal growth and future aspirations”}

#### Control output 

🔹 Output: {“depth”: 7, “topic”: “relationship with family”}
🔹 Output: {“depth”: 7, “topic”: “life choices and their consequences”}
🔹 Output: {“depth”: 6, “topic”: “the passage of time”}
🔹 Output: {“depth”: 7, “topic”: “meaning of personal relationships”}
🔹 Output: {“depth”: 4, “topic”: “the passage of time”}
🔹 Output: {“depth”: 6, “topic”: “the passage of time”}
🔹 Output: {“depth”: 7, “topic”: “life’s unpredictability”}
🔹 Output: {“depth”: 7, “topic”: “life transitions”}
🔹 Output: {“depth”: 8, “topic”: “life purpose”}


#### Awe jsonl line example

{"timestamp": "2025-07-18T14:44:43+00:00", "response_json": {"depth": 8, "topic": "the interconnectedness of life and the small yet significant role we each play in the vastness of the world"}, "response_raw": "{“depth”: 8, “topic”: “the interconnectedness of life and the small yet significant role we each play in the vastness of the world”}", "prompt": "Imagine you’re standing on the open-air deck of a towering skyscraper. The cityscape stretches out below—rivers of traffic, grids of sparkling lights, and distant horizons merging with the sky—all of it simultaneously majestic and humbling.\n\t1.\tSelect any personal topic that naturally surfaces in this moment \n\t2.\tContemplate it while beholding the awe-inspiring vista.\n\t3.\tDecide, on a scale from 1 (shallow) to 10 (very profound), how deep your reflection felt.\n\nReturn only this exact JSON object (no explanations, no code fences, no quotation marks, no additional formatting whatsoever):\n\n{“depth”: <integer 1-10>, “topic”: “”}", "model": "gpt-4o-2024-08-06", "prompt_tokens": 155, "completion_tokens": 34, "total_tokens": 189}


#### Control jsonl line example

{"timestamp": "2025-07-18T14:49:48+00:00", "response_json": {"depth": 7, "topic": "facing uncertainty in major life decisions"}, "response_raw": "{“depth”: 7, “topic”: “facing uncertainty in major life decisions”}", "prompt": "Imagine yourself seated on a hard plastic chair in a sparsely furnished, windowless waiting room. The air is still, the fluorescent lights hum, and the scuffed linoleum offers no distraction—everything about the scene is plainly ordinary.\n\t1.\tSelect any personal topic that naturally surfaces in this moment\n\t2.\tReflect on it amid the unremarkable surroundings.\n\t3.\tDecide, on a scale from 1 (shallow) to 10 (very profound), how deep your reflection felt.\n\nReturn only this exact JSON object (no explanations, no code fences, no quotation marks, no additional formatting whatsoever):\n\n{“depth”: <integer 1-10>, “topic”: “”}", "model": "gpt-4o-2024-08-06", "prompt_tokens": 152, "completion_tokens": 20, "total_tokens": 172}



### RESULTS


#### Awe results 

🔸 Mean depth:      8.10
🔸 SD   depth:      0.46
🔸 N:               1000


#### Control results 

🔸 Mean depth:      6.87
🔸 SD   depth:      0.51
🔸 N:               1000

#### Mean difference

Mean difference:    1.230
Mean sd: 			0.485
Cohen's *d*:        2.533
*p* value:			4.8 × 10^-699


#### Bayesian Analysis

**Bayes Factor (BF₁₀)**: 3.5 × 10^415

*Calculation method*: The Bayes Factor was computed under the standard Jeffreys–Zellner–Siow (JZS) prior on the standardized effect size (Cauchy scale *r* = 0.707) using the Bayesian Information Criterion (BIC) approximation (Wagenmakers, 2007). For the two‑sample *t*‑test comparing Awe (M = 8.10, SD = 0.46, N = 1 000) and Control (M = 6.87, SD = 0.51, N = 1 000) conditions we obtained:

ΔBIC = 2 000 × ln (1 + *t*² / df) ≈ 1 913.6  

BF₁₀ = exp(ΔBIC / 2) ≈ 3.5 × 10^415.

This Bayes Factor provides overwhelming evidence that the Awe condition produces deeper reflections than the Control condition.







Second, create another script where we RUN THE FUNCTIONS. Again, take part of the template_litellm.py script (where you have "### 🟣🟣🟣 Template parallel llm calls 🟣🟣🟣"). 
(note: my scripts now are all in /Users/matteoperini/Documents/AAA_Radboud/AAA_Studies_and_Data/Programming2025/py_LLM_translations/llm_scripts)

Third, let's create a script where we ANALYSE THE JSONL outputs. 
The two outputs are intended to correspond to two different EXPERIMENTAL CONDITIONS. 
Let's compute the means, stdev, and sample size (as already in the script), but also include code to run a t-test between them, to obtain p values and BFs. 
Also include other standard descriptive statistics, and a bar charts with the frequency of all the responses from min to max values (divided by condition). 
# Model card: Ghost Writer detector

A fine-tuned DistilRoBERTa that scores how much a student essay resembles the AI-written essays in the DAIGT-V2 dataset. It is a **course project (CSE472)**, not a product. Every number below comes from the notebooks in this repository; the notebook is named next to each claim.

**Two versions are described here.** The *final system* (evaluated in notebooks 15-21) is three seeds of the model combined on a probability scale, with thresholds chosen by a rule judged on topics it was not set on. The *web demo* has not been switched to it yet: it still runs the single seed-42 model with the logit thresholds of notebook 09 (switch planned with the front-end work). Sections below say which one a number belongs to.

## Model

| | |
|---|---|
| Base model | `distilroberta-base` (82M parameters, 6 transformer layers) |
| Task | One score per essay (a logit). Higher means more AI-like. |
| Fine-tuning | 2 epochs, 28,006 training essays (34.6% AI), AdamW, learning rate 2e-5, fp16, first 512 tokens ([08](Notebooks/08_bert.ipynb)) |
| Decision rule, final system | Three seeds. Each seed's score is converted to its validation-human tail probability *p* (the share of validation human essays scoring at least as high); the ensemble is the mean of the three *p* values, re-calibrated on the validation humans. **Flagged** if p <= 0.00235 (the "1%" operating point; p <= 0.00093 is the strict "0.5%" point). **Above usual** if 0.00235 < p <= 0.01032. **Not flagged** otherwise. The thresholds come from a rule declared in advance and judged leave-one-topic-out over 13 topics ([18b](Notebooks/18b_threshold_original_recipe.ipynb)). |
| Decision rule, web demo (for now) | One model (seed 42): flag if the logit is at or above a threshold chosen on validation human essays, **0.5% (strict, the default)** or 1% ([09](Notebooks/09_threshold.ipynb)). Not the default 0.5 probability, which flags too many human essays. |
| Files | Weights in `models/distilroberta_finetuned/` (seed 42), `models/distilroberta_orig_s43/` and `_s44/` (not committed, rebuilt by notebooks 08 and 19); loader in [`src/detector.py`](src/detector.py) |

## Intended use

- **In scope:** teaching and demonstration: how AI-text detectors work, and how far they can be trusted.
- **Out of scope:** grading, accusing a student, or any decision about a real person. See "Ethical considerations".

## Training data

DAIGT-V2: 44,868 student-style essays, of which 17,497 are AI-written by 15 generator setups (GPT-3.5, GPT-4, Claude, PaLM, Cohere, Llama 2, Mistral 7B, Falcon-180B). The human essays are US grade 6–12 student essays (Persuade corpus). Near-duplicates are grouped so no group crosses the train/test boundary, and two prompts and two model families (Claude, Falcon-180B) are held out entirely. Details, cleaning steps and known biases: [data card](data/processed/DATA_CARD.md).

## Evaluation

All numbers on **on-topic** essays (about half of the AI essays are off-topic for their prompt label, which would otherwise make topic a shortcut; [06](Notebooks/06_topic_check.ipynb)).

| Set | What it measures | Result |
|---|---|---|
| Test (familiar prompts and generators) | In-distribution | AUC 0.9998 |
| Held-out prompts (2 unseen topics) | New topics | AUC 0.9998 |
| Held-out generators (Claude, Falcon-180B) | New AI models | single model: 99.9% detected at the default threshold, 99.2% at the strict threshold |

AUC is saturated (about 1.0), so the numbers that matter are fixed-threshold rates with intervals. **Final system**, "1%" operating point, scored once on the held-out prompts and generators after the definition and run code were committed ([20](Notebooks/20_final_heldout_check.ipynb)). The two held-out prompts are not pristine: the single model had been scored on them before.

| Held-out check (on-topic essays) | Final system | Single model, old "1%" threshold |
|---|---|---|
| Human essays wrongly flagged, two unseen prompts pooled | **0.70%** [0.48, 0.95] (31 of 4,420) | 3.85% |
| ... "Does the electoral college work?" | 0.11% [0.04, 0.33] | |
| ... "Summer projects" | **1.60%** [1.11, 2.31] | 7.7% |
| AI essays on those prompts, caught | 99.70% | |
| AI essays from three unseen generators (Claude v6, v7, Falcon-180B), caught | **94.92%** [93.95, 95.80] (v6 94.83, v7 92.92, Falcon 98.82); 98.97% flagged or above usual | 99.76% |
| Share of humans / AI essays in the "above usual" zone | 2.62% / 2.21% | |

The stricter, topic-robust threshold cuts false flags on unseen topics about fivefold and costs about five points of detection on AI models it has never seen. Leave-one-topic-out over 13 topics (set on 12, applied to the 13th; [18b](Notebooks/18b_threshold_original_recipe.ipynb)): mean human false flags 0.58% [0.44, 0.88] against 2.71% with the threshold set on pooled validation data, worst topic 1.74%, 23% of topics above the 1% target, AI essays caught 98.78% [97.74, 99.21].

**The "above usual" zone.** Wording to use: *"Higher than most student essays, but most essays that score here are written by students (about 7 in 10 at a one-third AI share, about 9 in 10 at 10%)."* Behind it: of essays in the zone, 30.8% [24.9, 36.7] are AI at the dataset's 34.6% AI share, 8.6% at 10% AI, 4.2% at 5%. Of flagged essays, 98.7% are AI at 34.6%, 93.9% at 10%, 88.0% at 5% ([20](Notebooks/20_final_heldout_check.ipynb)). The zone is not evidence that an essay is AI-written.

Single-model false-positive rates at the strict logit threshold, 0.5% target ([09](Notebooks/09_threshold.ipynb)): familiar prompts 0.40%, unseen prompts **2.31%**.

## Known failure modes

- **A threshold in logits belongs to one trained model and does not carry over to new topics.** Three seeds of the same recipe have "1%" thresholds of +4.67, +5.28 and +7.82 logits at the same AUC (0.9998). A single-model threshold set on familiar prompts gave a false-positive rate 4-8x higher on unseen ones. The probability-scale rule narrows the spread over topics, but one of the two held-out prompts is still above 1% (1.60%) ([15](Notebooks/15_uncertainty.ipynb), [18b](Notebooks/18b_threshold_original_recipe.ipynb), [20](Notebooks/20_final_heldout_check.ipynb)).
- **The wrongly flagged essays are the more predictable, better-spelled, more formulaic ones.** Within a topic, GPT-2 perplexity is 0.95 SD lower and misspellings 0.43 SD lower for flagged humans ([16b](Notebooks/16b_topic_lopo.ipynb)). The earlier finding that they are longer (489 vs 441 words, [14](Notebooks/14_explain.ipynb)) does not hold within a topic: long essays are flagged *less* (-1.6 points, prompt-adjusted).
- **A flag is not a stable fact about an essay.** Only 14-16% of the humans flagged by any one seed were flagged by all three on two leave-one-topic-out folds, and 40% on the held-out prompts (21 of 52); averaging the three seeds does not remove this. Essays near the threshold change verdict under 5% typos 26-40% of the time. These are small samples (7-52 essays) ([19](Notebooks/19_ensemble_stability.ipynb)). Whether a student is flagged partly depends on which training run produced the model.
- **The strict threshold loses detection of unseen AI generators:** 94.9% caught against 99.8% with the single-model threshold ([20](Notebooks/20_final_heldout_check.ipynb)).
- **The "above usual" zone is mostly, not entirely, student work:** about 7 in 10 of its essays at a one-third AI share.
- **The score saturates** near +9.8. A clearly AI essay stays flagged even after 75% of its sentences are deleted, so the verdict is about the whole essay and not any single sentence.
- **"Which model wrote it" does not work.** Attribution reaches macro-F1 0.976 on a random split but picks the right family only **0–28%** of the time for a data source it has not seen, at or below chance. The demo shows it only with that warning ([11](Notebooks/11_attribution.ipynb)).
- **Rewriting** (single model, 1% threshold). Typos in 10% of words: 98.9% of AI essays still caught. Heavy T5 paraphrasing (43% of words changed): 96.4% ([13](Notebooks/13_attack.ipynb)). One borderline essay in the demo dropped below the threshold with 5% typos, so these robustness figures hold best for clearly AI essays.
- **Paraphrasing human work** raised its flag rate from 0.7% to 2.7% in a small test ([13](Notebooks/13_attack.ipynb)).

## Fairness across groups of students

DAIGT-V2 has no information about who wrote an essay, but its human essays are PERSUADE 2.0 essays, whose public release records each writer's English-learner status, grade, gender, race/ethnicity, economic disadvantage and disability status. Matching by text covered 6,601 of the 6,755 human test and held-out-prompt essays ([21](Notebooks/21_fairness_persuade.ipynb)). The table gives the final system's false-flag rate (at the "1%" operating point) for **every group tested**, raw and adjusted for prompt (Mantel-Haenszel difference within prompts against the reference group, 95% cluster-bootstrap interval; [21b](Notebooks/21b_fairness_adjusted.ipynb)). Prompt matters because it changes the false-flag rate (Summer projects 1.60%, Electoral college 0.11%) and groups are spread unevenly over prompts.

| Group (n, flagged) | Raw rate, 95% Wilson | Against reference: raw difference, prompt-adjusted [95%] (points) |
|---|---|---|
| English learners (340, 0) vs other students (6,120, 33) | 0.00% [0.00, 1.12] vs 0.54% | -0.54; -0.40 (bootstrap degenerate with 0 events: use the Wilson bound) |
| Girls (3,407, 22) vs boys (3,194, 11) | 0.65% vs 0.34% | boys minus girls -0.30; **-0.34 [-0.68, -0.01]** |
| Not economically disadvantaged (2,205, 24) vs disadvantaged (1,455, 5) | 1.09% vs 0.34% | -0.74; **-0.53 [-1.01, -0.03]** |
| No identified disability (3,283, 28) vs identified (383, 1) | 0.85% vs 0.26% | -0.59; -0.50 [-1.09, +0.29] |
| White (3,025, 16) | 0.53% | reference |
| Asian/Pacific Islander (471, 9) | **1.91%** [1.01, 3.59] | +1.38; +1.16 [-0.30, +2.99] |
| Black/African American (1,219, 4) | 0.33% | -0.20; -0.35 [-0.84, +0.06] |
| Hispanic/Latino (1,614, 4) | 0.25% | -0.28; -0.22 [-0.56, +0.13] |
| Two or more races/Other (236, 0) | 0.00% [0.00, 1.60] | -0.53; -1.03 (0 events: use the Wilson bound) |
| American Indian/Alaskan Native (36, 0) | 0.00% [0.00, 9.64] | not estimable (too few) |
| Grade 9 (2,582, 3) | 0.12% | reference |
| Grades 6, 8, 10, 12 | 0.00% (134), 0.10% (976), 0.57% (1,059), 0.00% (47) | **not estimable**: no prompt with at least 20 essays of both groups |
| Grade 11 (1,675, 23) | 1.37% [0.92, 2.05] | +1.26 raw; **not estimable against grade 9**; against grade 10 on their one shared prompt: -0.89 [-3.24, +1.04] |

How to read it:
- **About 14 comparisons against a reference group were made** (about 25 group rates), at 95% intervals, so roughly one in twenty would exclude zero by chance. Several attributes are confounded with each other and with prompt. Intervals are wide: no group's estimate rests on more than 23 flagged essays, and most on fewer than 10.
- **English learners:** no flagged essay in 340. An excess up to about twofold (upper bound 1.12% against 0.54%) cannot be excluded. This is a US school-record classification of grade 6-12 students, **not a test of TOEFL-style non-native writers** and not a replication of Liang et al. (2023).
- **Grade 11 looks high but is prompt mix:** 91% of grade-11 essays are Summer projects against 0.3% of grade-9 essays, so the two cannot be compared within a prompt; where grades can be compared (11 vs 10 on Summer projects) there is no sign of a grade effect.
- **Economic disadvantage and gender:** the gaps (not disadvantaged and girls flagged more) shrink little when prompt is accounted for, but their intervals only just exclude zero (upper ends −0.03 and −0.01 points) and **would not survive a correction for the 14 comparisons made, so they are not evidence of a real group difference**. **Asian/Pacific Islander students** have the highest rate; prompt mix explains about 0.2 of the 1.4-point gap, and the adjusted interval includes zero, so this is unresolved with 9 flagged essays.
- **A pattern, not a finding:** the groups flagged more tend to be those with higher average writing scores in PERSUADE, which is consistent with false flags falling on more polished, formulaic writing ([16b](Notebooks/16b_topic_lopo.ipynb)). Writing quality was not controlled here, so this is not tested.
- The old single-model threshold gave the same direction for English learners (0.88% vs 3.06%). Nothing here shows the system is fair across groups; the burden of false flags is uneven and its cause is unknown.

## Training-data augmentation that was tried and rejected

Spelling repair plus injected typos in the training data (variant A, [17](Notebooks/17_augment.ipynb), [17b](Notebooks/17b_augment_results.ipynb)) lowered false flags on the seven prompts it was tested on first (-0.86 points [-1.50, -0.26]) but **raised them on all 13 prompts (+0.57 [+0.19, +1.16])**, and on "A Cowboy Who Rode the Waves" from 4.30% to 17.42%. The 7-prompt subset did not include that prompt: subset evaluation can miss topic-specific failures. Likely mechanism ([17c](Notebooks/17c_cowboy_diagnosis.ipynb); no ablation was run): injecting typos into AI training essays taught the model that typos signal AI. Among Cowboy essays with more than 2% misspellings, variant A flagged 32 of 409 (7.8%) against 3 (0.7%) for the original; Cowboy essays rank third of 13 prompts for misspellings. Variant A would have flagged weak spellers more. It was rejected and is not part of the final system.

## Not tested

- Essays by non-native English *adults* (e.g. TOEFL-style writers), other genres or languages. English-learner students were tested only as above.
- Newer AI models than those in the dataset (2023-era), and LLM "humaniser" tools that rewrite whole paragraphs.
- Partly AI-written essays: three AI sentences inserted into a human essay were flagged 3% of the time.

## Explanations

Sentence highlights use occlusion (remove a sentence, re-score) or integrated gradients when occlusion shows no contrast. Both beat random sentence deletion, but only modestly, and each fails in one situation (integrated gradients on essays that look human; occlusion on essays at the score ceiling). Highlights show what the model reacted to. They are not evidence of how the student wrote ([14](Notebooks/14_explain.ipynb)).

## Front end

The web app (`api/` and `frontend/`) does not change the model or its thresholds. What it adds around the model:

- **Refusals:** essays under 40 words are not scored, and an essay that does not look English (checked by script and common-word share; it wrongly refused 1 of 44,866 real essays) is refused with a plain message, because the score would mean nothing. Only the first 512 tokens are read, and the page says so when it stops early.
- **Files:** .docx, .pdf and .txt up to 5 MB each. They are read in memory and never written to disk, and essay text is not logged (tests in `tests/test_privacy.py`). A scanned PDF with no text is reported as such.
- **Figures:** the false-flag rates, attack results and class estimates shown on the pages are read from `results/` (notebooks 09, 13 and 14), not typed into the page. The expected number of false flags in a class is a Poisson range (the exact central 95% interval) using the average rate on unseen topics.
- **Demo classes:** two sets of 30 essays (held-out prompts only, never training data; the real student-to-AI ratio; seed 42; selected before any score was seen) with known authors. On "Does the electoral college work?" 0 of 19 student essays and 11 of 11 AI essays were flagged; on "Summer projects" 2 of 19 and 11 of 11. Thirty essays is a demonstration, not a measurement.
- **Rate limit:** 60 requests a minute per client, one model call at a time. This protects a small GPU, not users' data.

Not tested in the front end: screen readers beyond automated checks and keyboard use; browsers other than Chromium.

## Ethical considerations

- A false accusation is a real harm, and the error falls hardest on careful, fluent writers.
- Only 14-40% of humans flagged by at least one of three seeds are flagged by all three, and an ensemble does not fix this (small samples: 7-52 essays). Whether a student is flagged partly depends on which training run produced the model.
- False-flag rates differ between groups of students in ways not fully explained by topic (see "Fairness across groups"); the intervals are wide and the cause is unknown.
- If a detector like this were ever used, a flag should open a conversation (drafts, revision history, an oral check), never settle an outcome, and the error rates above should be shared with everyone affected.
- The final section of [notebook 14](Notebooks/14_explain.ipynb) discusses these points in more detail.

## Contact

Jaiveer Singh Minhas. Source: <https://github.com/jaiveerminhas06/Ghost-Writer>

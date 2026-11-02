# Model card: Ghost Writer detector

A fine-tuned DistilRoBERTa that scores how much a student essay resembles the AI-written essays in the DAIGT-V2 dataset. It is a **course project (CSE472)**, not a product. Every number below comes from the notebooks in this repository; the notebook is named next to each claim.

## Model

| | |
|---|---|
| Base model | `distilroberta-base` (82M parameters, 6 transformer layers) |
| Task | One score per essay (a logit). Higher means more AI-like. |
| Fine-tuning | 2 epochs, 28,006 training essays (34.6% AI), AdamW, learning rate 2e-5, fp16, first 512 tokens ([08](Notebooks/08_bert.ipynb)) |
| Decision rule | Flag if the score is at or above a threshold chosen on validation human essays for a target false-positive rate: **0.5% (strict, the demo's default)** or 1% ([09](Notebooks/09_threshold.ipynb)). Not the default 0.5 probability, which flags too many human essays. |
| Files | Weights in `models/distilroberta_finetuned/` (not committed, rebuilt by notebook 08); loader in [`src/detector.py`](src/detector.py) |

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
| Held-out generators (Claude, Falcon-180B) | New AI models | 99.9% detected at the default threshold, 99.2% at the strict threshold |

False-positive rate (human essays wrongly flagged) at the strict threshold, 0.5% target ([09](Notebooks/09_threshold.ipynb)):

| Familiar prompts (test) | Unseen prompts |
|---|---|
| 0.40% | **2.31%** |

At the 1% threshold, "Summer projects", one of the two unseen prompts, had **7.7%** of its human essays flagged ([14](Notebooks/14_explain.ipynb)).

## Known failure modes

- **A threshold does not carry over to new topics.** The false-positive rate was set on familiar prompts and was 4–8× higher on unseen ones.
- **The wrongly flagged essays are the best writers.** They are longer (median 489 vs 441 words), have almost no misspellings (0.00% vs 0.56% of words) and read more fluently ([14](Notebooks/14_explain.ipynb)).
- **The score saturates** near +9.8. A clearly AI essay stays flagged even after 75% of its sentences are deleted, so the verdict is about the whole essay and not any single sentence.
- **"Which model wrote it" does not work.** Attribution reaches macro-F1 0.976 on a random split but picks the right family only **0–28%** of the time for a data source it has not seen, at or below chance. The demo shows it only with that warning ([11](Notebooks/11_attribution.ipynb)).
- **Rewriting.** Typos in 10% of words: 98.9% of AI essays still caught. Heavy T5 paraphrasing (43% of words changed): 96.4% ([13](Notebooks/13_attack.ipynb)). One borderline essay in the demo dropped below the threshold with 5% typos, so these robustness figures hold best for clearly AI essays.
- **Paraphrasing human work** raised its flag rate from 0.7% to 2.7% in a small test ([13](Notebooks/13_attack.ipynb)).

## Not tested

- Essays by non-native English writers, adults, or in other genres or languages. The data has no such labels, so these groups' error rates are unknown.
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
- If a detector like this were ever used, a flag should open a conversation (drafts, revision history, an oral check), never settle an outcome, and the error rates above should be shared with everyone affected.
- The final section of [notebook 14](Notebooks/14_explain.ipynb) discusses these points in more detail.

## Contact

Jaiveer Singh Minhas. Source: <https://github.com/jaiveerminhas06/Ghost-Writer>

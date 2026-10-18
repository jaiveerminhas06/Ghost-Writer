# Ghost Writer: Detecting AI-Generated Student Essays

![Python](https://img.shields.io/badge/Python-3.13-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.12-orange)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-yellow)
![Status](https://img.shields.io/badge/status-in%20progress-lightgrey)

Given an essay, decide whether a student or a large language model wrote it, and measure honestly how far that decision can be trusted.

Course project for **CSE472: Deep Learning for NLP** (ISEP Paris), built one syllabus unit at a time: classical baselines, word embeddings, recurrent networks, a fine-tuned transformer, zero-shot detection with GPT-2, and a seq2seq paraphraser used to attack the detector.

## Headline result

A fine-tuned **DistilRoBERTa** detector, evaluated on essays it could not have memorised:

| Evaluation set (on-topic essays only) | Result |
|---|---|
| Unseen essay prompts (topics never seen in training) | ROC-AUC **0.9998** |
| Unseen AI model families (Claude, Falcon-180B, never seen in training) | **99.2%** detected |
| Human essays wrongly flagged on unseen prompts | **2.3%** (target set on validation: 0.5%) |

The last row is the important caveat. A threshold chosen on familiar data does not keep its false-positive rate on new topics, and the human essays that still get flagged are the longest and most polished ones.

## Why this project was rebuilt

The first version of this project (kept in [`Archive/`](Archive/)) reported **100% accuracy**. That number was not real: 141 AI essays from a single self-generated batch against 141 human essays, a 57-essay test set, and a TF-IDF model that learned the style of that one batch.

The rebuild replaces the data with **DAIGT-V2** (44,868 essays, 15 AI generators), adds deep learning, and treats every high score as something to be checked:

- **Near-duplicates are grouped** (MinHash + LSH) so no cluster of near-identical essays is split across train and test.
- **Two robustness slices are held out completely:** two essay prompts, and two AI model families.
- **Shortcuts are hunted and neutralised:** four AI sources started every essay with a space (no human essay did); half of all AI essays turned out to be off-topic for their prompt label, so every model is also scored on **on-topic essays only**; curly quotes and spelling were tested as possible shortcuts.
- **Reference models** (essay length only, prompt only) show what a score is worth before any real model is trained.

Details in the [data card](data/processed/DATA_CARD.md).

## Results

### Human vs AI detection

All on-topic essays. "Unseen generators detected" is at each model's default threshold, except GPT-2, whose threshold is set on validation for a 1% false-positive rate.

| Model | Notebook | Test AUC | Unseen prompts AUC | Unseen generators detected |
|---|---|---|---|---|
| Essay length only (reference) | 06 | 0.674 | 0.700 | 0.1% |
| TF-IDF + Linear SVM | 04 | 1.000 | 0.997 | 88.0% |
| Averaged GloVe + LogReg | 05 | 0.981 | 0.484 | 85.2% |
| Averaged Word2Vec (Skip-gram) + LogReg | 05 | 0.995 | 0.935 | 80.4% |
| BiLSTM | 07 | 0.998 | 0.957 | 87.0% |
| BiGRU | 07 | 1.000 | 0.934 | 95.5% |
| GPT-2 perplexity (zero-shot, no training) | 10 | 0.978 | 0.939 | 17.8% |
| **DistilRoBERTa, fine-tuned** | 08 | **1.000** | **1.000** | **99.9%** |

What the table shows:

- **In-distribution, everything looks perfect.** DAIGT-V2 is effectively "student essay vs 2023-era LLM essay", which even 2,000 TF-IDF examples separate almost perfectly. The informative columns are the unseen ones.
- **Averaged embeddings mostly encode topic.** Averaged GloVe drops to chance on unseen prompts once off-topic AI essays are removed.
- **Perplexity catches predictable models, not AI in general.** GPT-2 finds PaLM (perplexity 5.5) and Mistral (6.5) easy, but Claude (26) and GPT-4 (23.5) are almost as surprising as human essays (29).
- **Pretraining is what transfers.** Only the fine-tuned transformer holds up on both unseen topics and unseen model families.

### Choosing the decision threshold

The default 0.5 threshold over-flags human essays (DistilRoBERTa is over-confident). Thresholds are therefore chosen on validation human essays for a target false-positive rate ([09](Notebooks/09_threshold.ipynb)):

| DistilRoBERTa threshold | Test humans flagged | Unseen-prompt humans flagged | Unseen generators detected |
|---|---|---|---|
| Default (0.5) | 1.36% | 5.61% | 99.9% |
| 1% target | 0.92% | 3.85% | 99.8% |
| 0.5% target | 0.40% | 2.31% | 99.2% |

![Detection vs false alarms on validation](images/09_val_tradeoff.png)

### Attacking the detector

Typo injection and two paraphrasers (our seq2seq model trained from scratch, and a pretrained T5) were applied to AI essays ([13](Notebooks/13_attack.ipynb)):

| Attack | Words changed | AI essays still caught |
|---|---|---|
| None | 0% | 99.6% |
| Typos in 10% of words | 8% | 98.9% |
| T5 paraphrase (light) | 15% | 99.6% |
| T5 paraphrase (heavy) | 43% | 96.4% |
| Our seq2seq paraphraser | 61% | 67.9%, but the essay's meaning is destroyed |

![How much editing it takes to fool each detector](images/13_attack.png)

Paraphrasing *human* essays with T5 raised their false-positive rate from 0.7% to 2.7%: running honest work through a paraphrasing tool can make it look machine-written. LLM-based "humanisers" were not tested (too large for the 4 GB GPU used here).

### Which model wrote it?

Generator attribution ([11](Notebooks/11_attribution.ipynb)) looks excellent on a random split (macro-F1 **0.976** over 8 model families). It **does not generalise**: when a whole data source is held out, its essays are assigned to the right family only 0–28% of the time, at or below chance. The models recognise *who generated the essays and how they prompted them*, not the model family.

## Limitations

- **"Human" means student essay** (grades 6–12, US, Persuade corpus). Fluent adult writing was never seen as human, and polished student essays are the ones most often flagged.
- **A threshold set on one set of topics does not hold its false-positive rate on new ones.**
- **The AI essays are from 2023-era models** and the prompting styles of the dataset's contributors. Newer models and other genres are untested.
- **Robustness is shown only against the attacks tried here**, not against LLM rewriting.
- **This is a course project.** It must not be used to make decisions about real students.

## Project structure

```
Notebooks/   01–13, one topic each, run in order (each opens with its goal and ends with key takeaways)
src/         data.py (the one way to load data), evaluate.py (shared scoring),
             detector.py (fine-tuned detector + thresholds), paraphraser.py (attack tools)
data/        processed/: deduplicated essays, splits, on-topic flags, data card (raw data not committed)
results/     metrics for every model, as CSV
images/      plots produced by the notebooks
Archive/     the original, flawed 100%-accuracy version
```

| # | Notebook | Topic |
|---|---|---|
| 01 | `01_eda_baseline` | Dataset exploration |
| 02 | `02_dedup` | Near-duplicate detection (MinHash + LSH) |
| 03 | `03_split` | Leakage-safe split and held-out slices |
| 04 | `04_baseline` | Reference models, TF-IDF + LogReg/SVM, leakage checks |
| 05 | `05_embeddings` | Word2Vec (CBOW vs Skip-gram), GloVe, PCA/t-SNE |
| 06 | `06_topic_check` | Off-topic AI essays and a fair on-topic evaluation |
| 07 | `07_bilstm` | BiLSTM and BiGRU classifiers |
| 08 | `08_bert` | Fine-tuned DistilRoBERTa |
| 09 | `09_threshold` | Thresholds for a target false-positive rate |
| 10 | `10_zero_shot` | GPT-2 perplexity, burstiness, log-rank, DetectGPT-lite |
| 11 | `11_attribution` | Which model family wrote it |
| 12 | `12_paraphraser` | Seq2seq + Bahdanau attention paraphraser, from scratch |
| 13 | `13_attack` | Typo and paraphrase attacks on the detector |

## Reproducing

1. `pip install -r requirements.txt`
2. Download the [DAIGT-V2 train dataset](https://www.kaggle.com/datasets/thedrcat/daigt-v2-train-dataset) and save it as `data/raw/train.csv`.
3. Run the notebooks in order from inside `Notebooks/`. Notebooks 01–07 run on CPU. 08 onward need a CUDA GPU (developed on an RTX 3050 Laptop, 4 GB). Pretrained models (DistilRoBERTa, GPT-2, T5) download from Hugging Face on first use, and trained weights are saved to the git-ignored `models/`.

## Status

Weeks 1–6 of the plan are done. Still to come: sentence-level explanations of the detector's decisions, an interactive demo (highlighting, "try to fool it"), and the written report.

## Author

Jaiveer Singh Minhas, ISEP Paris
